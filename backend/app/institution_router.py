"""
BOU Sentinel - Backward-compatible institution API routes
Translates refactored schema to the field names the frontend expects.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db

router = APIRouter(prefix="/api/institutions", tags=["Institutions"])


def _translate(d):
    """Translate a refactored Institution dict to frontend-compatible field names."""
    d["institution_name"] = d.pop("name", "")
    d["overall_risk_score"] = d.get("risk_score")
    d["compliance_score"] = round(100 - (d.get("risk_score") or 0), 1)
    score = d.get("risk_score") or 0
    if score < 25:
        d["compliance_status"] = "compliant"
    elif score < 50:
        d["compliance_status"] = "warning"
    else:
        d["compliance_status"] = "non_compliant"
    return d


@router.get("/", summary="List all institutions")
async def list_institutions(
    tier: str | None = Query(None),
    status: str | None = Query(None),
    region: str | None = Query(None),
    search: str | None = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    from app.regulatory_models import Institution
    query = db.query(Institution)
    if tier:
        query = query.filter(Institution.tier == tier)
    if search:
        query = query.filter(
            (Institution.institution_code.ilike(f"%{search}%"))
            | (Institution.name.ilike(f"%{search}%"))
        )
    total = query.count()
    return {"total": total, "institutions": [_translate(i.to_dict()) for i in query.offset(skip).limit(limit).all()]}


@router.get("/summary", summary="Sector-wide compliance summary")
async def get_sector_summary(db: Session = Depends(get_db)):
    from app.regulatory_models import Institution
    dicts = [_translate(i.to_dict()) for i in db.query(Institution).all()]
    total = len(dicts)
    if total == 0:
        return {"total_institutions": 0, "compliant_count": 0, "warning_count": 0, "under_review_count": 0,
                "non_compliant_count": 0, "suspended_count": 0, "compliance_rate_pct": 0,
                "non_compliance_rate_pct": 0, "average_risk_score": 0, "average_compliance_score": 0}
    c = {"compliant": 0, "warning": 0, "under_review": 0, "non_compliant": 0}
    for d in dicts:
        s = d.get("compliance_status", "compliant")
        if s in c: c[s] += 1
    avg_risk = round(sum(d.get("overall_risk_score") or 0 for d in dicts) / total, 1)
    avg_c = round(sum(d.get("compliance_score") or 0 for d in dicts) / total, 1)
    return {
        "total_institutions": total,
        "compliant_count": c["compliant"],
        "warning_count": c["warning"],
        "under_review_count": c["under_review"],
        "non_compliant_count": c["non_compliant"],
        "suspended_count": 0,
        "compliance_rate_pct": round(c["compliant"] / total * 100, 1),
        "non_compliance_rate_pct": round((c["non_compliant"]) / total * 100, 1),
        "average_risk_score": avg_risk,
        "average_compliance_score": avg_c,
    }


@router.get("/tiers", summary="Breakdown by regulatory tier")
async def get_tier_breakdown(db: Session = Depends(get_db)):
    from app.regulatory_models import Institution
    results = []
    for tier_key, in db.query(Institution.tier).distinct():
        rows = db.query(Institution).filter(Institution.tier == tier_key).all()
        count = len(rows)
        compliant = sum(1 for r in rows if (r.risk_score or 0) < 25)
        nc = sum(1 for r in rows if (r.risk_score or 0) >= 75)
        w = sum(1 for r in rows if 50 <= (r.risk_score or 0) < 75)
        results.append({
            "tier": tier_key,
            "tier_name": tier_key,
            "total_institutions": count,
            "compliant_count": compliant,
            "at_risk_count": nc + w,
            "compliance_rate_pct": round(compliant / count * 100, 1) if count else 0,
            "average_risk_score": round(sum((r.risk_score or 0) for r in rows) / count, 1) if count else 0,
            "average_compliance_score": round(sum(100 - (r.risk_score or 0) for r in rows) / count, 1) if count else 0,
        })
    return {"tiers": results}


@router.get("/at-risk", summary="Institutions with compliance issues")
async def get_at_risk(limit: int = 50, db: Session = Depends(get_db)):
    from app.regulatory_models import Institution
    institutions = db.query(Institution).filter(Institution.risk_score >= 50).order_by(Institution.risk_score.desc()).limit(limit).all()
    return {"count": len(institutions), "institutions": [_translate(i.to_dict()) for i in institutions]}


@router.get("/{institution_code}", summary="Get institution details")
async def get_institution(institution_code: str, db: Session = Depends(get_db)):
    from app.regulatory_models import Institution
    inst = db.query(Institution).filter_by(institution_code=institution_code).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    return _translate(inst.to_dict())


@router.post("/seed", summary="Seed database with BOU institutions")
async def seed(db: Session = Depends(get_db)):
    from app.seed_institutions import seed_institutions
    try:
        count = seed_institutions(db)
        return {"message": f"Seeded {count} institutions", "total": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{institution_code}/refresh", summary="Refresh compliance metrics")
async def refresh(institution_code: str, db: Session = Depends(get_db)):
    from app.regulatory_models import Institution
    from app.seed_institutions import SEED_INSTITUTIONS
    from app.compliance_engine import calculate_compliance_risk
    inst = db.query(Institution).filter_by(institution_code=institution_code).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    seed_data = next((i for i in SEED_INSTITUTIONS if i["institution_code"] == institution_code), None)
    if seed_data:
        risk_score, risk_level, issues = calculate_compliance_risk(
            seed_data, fraud_stats={
                "fraud_rate": inst.fraud_rate / 100 if inst.fraud_rate else 0,
                "total_transactions": inst.total_transactions or 0,
                "fraud_transactions": inst.fraud_transactions or 0,
            },
        )
        inst.risk_score = risk_score
        inst.risk_level = risk_level
        inst.set_issues(issues)
        inst.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(inst)
    return _translate(inst.to_dict())