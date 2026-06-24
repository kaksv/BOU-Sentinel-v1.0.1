"""
BOU Sentinel - Institution Monitoring API Routes
Provides REST endpoints for regulated institution compliance monitoring.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.database import get_db
# These would be imported from the respective files in a real project:
# from app.institution_models import RegulatedInstitution, ComplianceStatus
# from app.institution_service import SEED_INSTITUTIONS, BOU_THRESHOLDS, generate_compliance_metrics, get_sector_summary

logger = logging.getLogger("bou-sentinel.institutions")

router = APIRouter(prefix="/api/institutions", tags=["Institution Monitoring"])


@router.get("/", summary="List all regulated institutions")
async def list_institutions(
    tier: Optional[str] = Query(None, description="Filter by tier: tier_1, tier_2, tier_3, tier_4, forex_bureau, money_remitter, payment_provider, credit_reference"),
    status: Optional[str] = Query(None, description="Filter by compliance status: compliant, warning, under_review, non_compliant, suspended"),
    region: Optional[str] = Query(None, description="Filter by region"),
    search: Optional[str] = Query(None, description="Search by institution name or code"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    Retrieve all BOU-regulated institutions with their live compliance metrics.
    Supports filtering by tier, compliance status, region, and text search.
    """
    from app.institution_models import RegulatedInstitution

    query = db.query(RegulatedInstitution).filter(RegulatedInstitution.is_active == True)

    if tier:
        query = query.filter(RegulatedInstitution.tier == tier)
    if status:
        query = query.filter(RegulatedInstitution.compliance_status == status)
    if region:
        query = query.filter(RegulatedInstitution.region.ilike(f"%{region}%"))
    if search:
        query = query.filter(
            or_(
                RegulatedInstitution.institution_name.ilike(f"%{search}%"),
                RegulatedInstitution.institution_code.ilike(f"%{search}%"),
            )
        )

    total = query.count()
    institutions = (
        query.order_by(RegulatedInstitution.overall_risk_score.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "institutions": [inst.to_dict() for inst in institutions],
    }


@router.get("/summary", summary="Sector-wide compliance summary")
async def get_sector_summary(db: Session = Depends(get_db)):
    """
    Returns sector-wide aggregated compliance statistics for the BOU dashboard.
    Powers the top-level KPI cards and tier breakdown charts.
    """
    from app.institution_models import RegulatedInstitution

    institutions = db.query(RegulatedInstitution).filter(
        RegulatedInstitution.is_active == True
    ).all()

    inst_dicts = [i.to_dict() for i in institutions]

    from app.institution_service import get_sector_summary
    return get_sector_summary(inst_dicts)


@router.get("/at-risk", summary="Institutions with compliance issues")
async def get_at_risk_institutions(
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Returns institutions flagged as non-compliant, under review, or in warning state.
    Sorted by highest risk score descending for triage.
    """
    from app.institution_models import RegulatedInstitution

    institutions = (
        db.query(RegulatedInstitution)
        .filter(
            RegulatedInstitution.compliance_status.in_(["non_compliant", "warning", "under_review"]),
            RegulatedInstitution.is_active == True,
        )
        .order_by(RegulatedInstitution.overall_risk_score.desc())
        .limit(limit)
        .all()
    )

    return {
        "count": len(institutions),
        "institutions": [inst.to_dict() for inst in institutions],
    }


@router.get("/tiers", summary="Breakdown by regulatory tier")
async def get_tier_breakdown(db: Session = Depends(get_db)):
    """
    Returns compliance statistics broken down by regulatory tier.
    """
    from app.institution_models import RegulatedInstitution
    from app.institution_service import BOU_THRESHOLDS

    results = []
    for tier_key, tier_meta in BOU_THRESHOLDS.items():
        institutions = (
            db.query(RegulatedInstitution)
            .filter(
                RegulatedInstitution.tier == tier_key,
                RegulatedInstitution.is_active == True,
            )
            .all()
        )
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
            "governing_law": tier_meta["governing_law"],
            "min_capital_ugx_millions": tier_meta["min_capital_ugx_millions"],
        })

    return {"tiers": results}


@router.get("/{institution_code}", summary="Get institution details")
async def get_institution(institution_code: str, db: Session = Depends(get_db)):
    """Get full compliance profile for a specific institution."""
    from app.institution_models import RegulatedInstitution

    institution = (
        db.query(RegulatedInstitution)
        .filter(RegulatedInstitution.institution_code == institution_code)
        .first()
    )
    if not institution:
        raise HTTPException(status_code=404, detail=f"Institution {institution_code} not found")

    data = institution.to_dict()
    # Parse risk flags JSON for cleaner response
    if data.get("risk_flags"):
        try:
            data["risk_flags"] = json.loads(data["risk_flags"])
        except Exception:
            data["risk_flags"] = []
    else:
        data["risk_flags"] = []

    # Add thresholds for context
    from app.institution_service import BOU_THRESHOLDS
    data["regulatory_thresholds"] = BOU_THRESHOLDS.get(institution.tier, {})

    return data


@router.post("/seed", summary="Seed institution database with BOU institutions")
async def seed_institutions(db: Session = Depends(get_db)):
    """
    Populates the database with all BOU-regulated institutions and their
    initial compliance metrics. Safe to call multiple times (upserts).
    """
    from app.institution_models import RegulatedInstitution
    from app.institution_service import SEED_INSTITUTIONS, generate_compliance_metrics

    try:
        created = 0
        updated = 0

        for idx, inst_data in enumerate(SEED_INSTITUTIONS):
            existing = (
                db.query(RegulatedInstitution)
                .filter(RegulatedInstitution.institution_code == inst_data["institution_code"])
                .first()
            )

            metrics = generate_compliance_metrics(inst_data, seed_offset=idx * 7)

            if existing:
                for key, value in metrics.items():
                    setattr(existing, key, value)
                existing.updated_at = datetime.now(timezone.utc)
                updated += 1
            else:
                institution = RegulatedInstitution(
                    institution_code=inst_data["institution_code"],
                    institution_name=inst_data["institution_name"],
                    tier=inst_data["tier"],
                    license_number=inst_data.get("license_number"),
                    registered_address=inst_data.get("registered_address"),
                    region=inst_data.get("region"),
                    primary_regulator="Bank of Uganda",
                    **metrics,
                )
                db.add(institution)
                created += 1

        db.commit()
        logger.info(f"Institution seed: {created} created, {updated} updated")

        return {
            "message": f"Seeded {created} new institutions, updated {updated} existing",
            "total": created + updated,
        }
    except Exception as e:
        import traceback
        db.rollback()
        error_detail = traceback.format_exc()
        logger.error(f"Seed failed: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{institution_code}/refresh", summary="Refresh compliance metrics")
async def refresh_institution_metrics(institution_code: str, db: Session = Depends(get_db)):
    """
    Refreshes the compliance metrics for an institution (simulates real-time BOU data pull).
    In production this would connect to BOU's BSA (Bank Supervision Application).
    """
    from app.institution_models import RegulatedInstitution
    from app.institution_service import SEED_INSTITUTIONS, generate_compliance_metrics

    institution = (
        db.query(RegulatedInstitution)
        .filter(RegulatedInstitution.institution_code == institution_code)
        .first()
    )
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    # Find seed data to regenerate metrics
    seed_data = next(
        (i for i in SEED_INSTITUTIONS if i["institution_code"] == institution_code), None
    )
    if seed_data:
        import random
        metrics = generate_compliance_metrics(seed_data, seed_offset=random.randint(0, 999))
        for key, value in metrics.items():
            setattr(institution, key, value)
        institution.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(institution)

    return institution.to_dict()