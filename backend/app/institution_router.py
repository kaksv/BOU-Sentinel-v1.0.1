"""
BOU Sentinel - Backward-compatible institution API routes
Maps /api/institutions/* -> /api/regulatory/* so frontends continue to work
after the backend refactor that moved institution endpoints under /api/regulatory.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(prefix="/api/institutions", tags=["Institutions (legacy)"])


def _get_regulatory_summary(db: Session):
    # Import lazily to avoid circular imports
    from app.regulatory_models import Institution
    from app.institution_service import get_sector_summary  # noqa: F401 (may not exist)
    institutions = db.query(Institution).filter(Institution.is_active == True).all()
    return get_sector_summary([i.to_dict() for i in institutions])


@router.get("/", summary="List institutions (legacy alias)")
async def list_institutions(
    tier: str | None = Query(None),
    status: str | None = Query(None),
    region: str | None = Query(None),
    search: str | None = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    # Delegate to the regulatory router's logic via redirect
    from fastapi.responses import RedirectResponse
    params = []
    if tier: params.append(f"tier={tier}")
    if status: params.append(f"status={status}")
    if region: params.append(f"region={region}")
    if search: params.append(f"search={search}")
    params.append(f"skip={skip}")
    params.append(f"limit={limit}")
    qs = "&".join(params)
    return RedirectResponse(url=f"/api/regulatory/institutions?{qs}", status_code=307)


@router.get("/summary", summary="Sector summary (legacy alias)")
async def institution_summary(db: Session = Depends(get_db)):
    from app.regulatory_models import Institution
    from app.compliance_engine import calculate_compliance_risk, BOU_THRESHOLDS
    institutions = db.query(Institution).filter(Institution.is_active == True).all()
    inst_dicts = [i.to_dict() for i in institutions]
    # Build summary manually since get_sector_summary isn't exported
    total = len(inst_dicts)
    compliant = sum(1 for i in inst_dicts if i.get("compliance_status") == "compliant")
    warning = sum(1 for i in inst_dicts if i.get("compliance_status") == "warning")
    under_review = sum(1 for i in inst_dicts if i.get("compliance_status") == "under_review")
    non_compliant = sum(1 for i in inst_dicts if i.get("compliance_status") == "non_compliant")
    suspended = sum(1 for i in inst_dicts if i.get("compliance_status") == "suspended")
    avg_risk = sum(i.get("overall_risk_score", 0) for i in inst_dicts) / total if total else 0
    avg_compliance = sum(i.get("compliance_score", 0) for i in inst_dicts) / total if total else 0
    return {
        "total_institutions": total,
        "compliant_count": compliant,
        "warning_count": warning,
        "under_review_count": under_review,
        "non_compliant_count": non_compliant,
        "suspended_count": suspended,
        "compliance_rate_pct": round(compliant / total * 100, 1) if total else 0,
        "non_compliance_rate_pct": round((non_compliant + suspended) / total * 100, 1) if total else 0,
        "average_risk_score": round(avg_risk, 1),
        "average_compliance_score": round(avg_compliance, 1),
    }


@router.get("/tiers", summary="Tier breakdown (legacy alias)")
async def tier_breakdown(db: Session = Depends(get_db)):
    from app.regulatory_models import Institution
    from app.compliance_engine import BOU_THRESHOLDS
    results = []
    for tier_key, tier_meta in BOU_THRESHOLDS.items():
        institutions = db.query(Institution).filter(
            Institution.tier == tier_key,
            Institution.is_active == True,
        ).all()
        if not institutions:
            continue
        total = len(institutions)
        compliant = sum(1 for i in institutions if i.compliance_status == "compliant")
        at_risk = sum(1 for i in institutions if i.compliance_status in ("non_compliant", "warning"))
        avg_risk = sum(i.overall_risk_score for i in institutions) / total
        results.append({
            "tier": tier_key,
            "tier_name": tier_meta["name"],
            "total_institutions": total,
            "compliant_count": compliant,
            "at_risk_count": at_risk,
            "compliance_rate_pct": round(compliant / total * 100, 1),
            "average_risk_score": round(avg_risk, 1),
        })
    return {"tiers": results}


@router.get("/at-risk", summary="At-risk institutions (legacy alias)")
async def at_risk(limit: int = 50, db: Session = Depends(get_db)):
    from app.regulatory_models import Institution
    institutions = (
        db.query(Institution)
        .filter(
            Institution.compliance_status.in_(["non_compliant", "warning", "under_review"]),
            Institution.is_active == True,
        )
        .order_by(Institution.overall_risk_score.desc())
        .limit(limit)
        .all()
    )
    return {"count": len(institutions), "institutions": [i.to_dict() for i in institutions]}


@router.get("/{institution_code}", summary="Institution details (legacy alias)")
async def institution_detail(institution_code: str):
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/api/regulatory/institutions/{institution_code}", status_code=307)


@router.post("/seed", summary="Seed database (legacy alias)")
async def seed(db: Session = Depends(get_db)):
    from app.seed_institutions import seed_institutions
    try:
        count = seed_institutions(db)
        return {"message": f"Seeded {count} institutions", "total": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{institution_code}/refresh", summary="Refresh metrics (legacy alias)")
async def refresh(institution_code: str, db: Session = Depends(get_db)):
    from app.regulatory_models import Institution
    from app.compliance_engine import generate_compliance_metrics
    import random
    institution = db.query(Institution).filter_by(institution_code=institution_code).first()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    seed_data = next((i for i in SEED_INSTITUTIONS if i["institution_code"] == institution_code), None)
    if seed_data:
        metrics = generate_compliance_metrics(seed_data, seed_offset=random.randint(0, 999))
        for key, value in metrics.items():
            setattr(institution, key, value)
        institution.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(institution)
    return institution.to_dict()
