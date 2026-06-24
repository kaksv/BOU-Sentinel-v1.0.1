"""
BOU Sentinel - Regulatory Compliance Router
All endpoints for the Bank of Uganda institution supervision feature.

Endpoints:
  GET  /api/regulatory/institutions              — list all supervised institutions
  GET  /api/regulatory/institutions/{code}       — institution detail + compliance breakdown
  GET  /api/regulatory/institutions/{code}/reports — compliance report history
  PATCH /api/regulatory/institutions/{code}/metrics — update live financial metrics
  POST /api/regulatory/institutions/{code}/compliance-report — submit quarterly report
  GET  /api/regulatory/summary                   — regulator dashboard summary
  GET  /api/regulatory/risks                     — institutions sorted by risk score desc
  GET  /api/regulatory/non-compliant             — filter: only high/critical risk
"""
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.regulatory_models import ComplianceReport, Institution
from app.regulatory_schemas import (
    ComplianceReportCreate,
    ComplianceReportResponse,
    InstitutionMetricsUpdate,
    InstitutionResponse,
    RegulatoryDashboardResponse,
)
from app.compliance_engine import (
    BOU_THRESHOLDS,
    build_regulatory_summary,
    calculate_compliance_risk,
)
from app.ws_manager import manager

logger = logging.getLogger("bou-sentinel.regulatory")

router = APIRouter(prefix="/api/regulatory", tags=["Regulatory Compliance"])


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_institution_or_404(code: str, db: Session) -> Institution:
    inst = db.query(Institution).filter_by(institution_code=code.upper()).first()
    if not inst:
        raise HTTPException(
            status_code=404,
            detail=f"Institution '{code}' not found in BOU supervised registry",
        )
    return inst


async def _recalculate_and_broadcast(
    inst: Institution,
    db: Session,
    trigger: str,
    previous_risk_level: Optional[str] = None,
) -> None:
    """
    Re-run the compliance engine for an institution, persist, and broadcast
    a WebSocket compliance_alert if the risk level has changed or if fraud
    was detected.
    """
    risk_score, risk_level, issues = calculate_compliance_risk(
        inst.to_dict(),
        fraud_stats={
            "fraud_rate": inst.fraud_rate,
            "total_transactions": inst.total_transactions,
            "fraud_transactions": inst.fraud_transactions,
        },
    )

    inst.risk_score = risk_score
    inst.risk_level = risk_level
    inst.set_issues(issues)
    inst.last_risk_updated = datetime.now(timezone.utc)
    inst.updated_at = datetime.now(timezone.utc)
    db.add(inst)
    db.commit()
    db.refresh(inst)

    # Broadcast if risk changed or is elevated
    should_broadcast = (
        previous_risk_level != risk_level
        or risk_level in ("critical", "high")
        or trigger == "fraud_detected"
    )

    if should_broadcast:
        alert = {
            "type": "compliance_alert",
            "institution_code": inst.institution_code,
            "institution_name": inst.name,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "previous_risk_level": previous_risk_level,
            "tier": inst.tier,
            "trigger": trigger,
            "issues": issues[:5],   # top 5 issues in broadcast
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await manager.broadcast(json.dumps(alert))
        logger.info(
            f"📡 Compliance alert broadcast: {inst.institution_code} "
            f"→ {risk_level.upper()} ({risk_score:.1f}%)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# LIST & SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/institutions",
    summary="List all BOU-supervised institutions with compliance status",
)
async def list_institutions(
    tier: Optional[str] = None,
    risk_level: Optional[str] = None,
    license_status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    Returns all institutions supervised by the Bank of Uganda.
    Filterable by tier (Tier I / Tier II / Tier III / Non-Bank),
    risk_level (low / medium / high / critical), and license_status.
    Ordered by risk_score descending so highest-risk institutions appear first.
    """
    q = db.query(Institution)
    if tier:
        q = q.filter(Institution.tier == tier)
    if risk_level:
        q = q.filter(Institution.risk_level == risk_level)
    if license_status:
        q = q.filter(Institution.license_status == license_status)

    institutions = (
        q.order_by(Institution.risk_score.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [inst.to_dict() for inst in institutions]


@router.get(
    "/summary",
    response_model=RegulatoryDashboardResponse,
    summary="BOU regulator dashboard — aggregate compliance statistics",
)
async def regulatory_summary(db: Session = Depends(get_db)):
    """
    Aggregate compliance statistics for the BOU supervisor dashboard.
    Includes risk distribution, tier breakdown, and top-risk institutions.
    """
    all_institutions = db.query(Institution).all()
    summary = build_regulatory_summary(all_institutions)

    # Top 5 highest-risk institutions for the dashboard banner
    top_risk = (
        db.query(Institution)
        .filter(Institution.risk_level.in_(["critical", "high"]))
        .order_by(Institution.risk_score.desc())
        .limit(5)
        .all()
    )
    summary["top_risk_institutions"] = [
        {
            "institution_code": i.institution_code,
            "name": i.name,
            "tier": i.tier,
            "risk_score": i.risk_score,
            "risk_level": i.risk_level,
            "license_status": i.license_status,
            "issues_count": len(i.get_issues()),
        }
        for i in top_risk
    ]
    summary["ws_connected_clients"] = manager.count
    summary["generated_at"] = datetime.now(timezone.utc).isoformat()
    return summary


@router.get(
    "/risks",
    summary="All institutions sorted by risk score (highest first)",
)
async def get_risk_ranked_institutions(
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Returns all supervised institutions ranked by risk_score descending.
    Useful for the regulator's priority monitoring queue.
    """
    institutions = (
        db.query(Institution)
        .order_by(Institution.risk_score.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "rank": idx + 1,
            "institution_code": i.institution_code,
            "name": i.name,
            "tier": i.tier,
            "institution_type": i.institution_type,
            "license_status": i.license_status,
            "risk_score": i.risk_score,
            "risk_level": i.risk_level,
            "liquidity_ratio": i.liquidity_ratio,
            "core_capital_ratio": i.core_capital_ratio,
            "aml_compliance_status": i.aml_compliance_status,
            "fraud_rate": i.fraud_rate,
            "fraud_transactions": i.fraud_transactions,
            "total_transactions": i.total_transactions,
            "top_issue": (i.get_issues() or ["No issues detected"])[0],
            "issues_count": len(i.get_issues()),
            "last_risk_updated": (
                i.last_risk_updated.isoformat() if i.last_risk_updated else None
            ),
        }
        for idx, i in enumerate(institutions)
    ]


@router.get(
    "/non-compliant",
    summary="Institutions with HIGH or CRITICAL risk requiring BOU intervention",
)
async def get_non_compliant_institutions(db: Session = Depends(get_db)):
    """
    Returns institutions at HIGH or CRITICAL risk level.
    These are candidates for BOU Prompt Corrective Action (PCA) per the FIA 2004.
    """
    institutions = (
        db.query(Institution)
        .filter(Institution.risk_level.in_(["high", "critical"]))
        .order_by(Institution.risk_score.desc())
        .all()
    )
    return {
        "count": len(institutions),
        "prompt_corrective_action_candidates": [i.to_dict() for i in institutions],
        "bou_pca_reference": (
            "Financial Institutions Act 2004 s.88 — "
            "Prompt Corrective Actions for undercapitalised institutions"
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# INSTITUTION DETAIL
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/institutions/{institution_code}",
    summary="Full compliance detail for a specific supervised institution",
)
async def get_institution(
    institution_code: str,
    db: Session = Depends(get_db),
):
    """
    Returns the full regulatory profile including:
    - Current financial metrics (capital, liquidity)
    - AML/CFT compliance status
    - Corporate governance status
    - Computed risk score breakdown
    - BOU Sentinel fraud transaction stats
    """
    inst = _get_institution_or_404(institution_code, db)
    data = inst.to_dict()

    # Annotate with BOU threshold context for the frontend
    data["bou_thresholds"] = {
        "core_capital_ratio_min": BOU_THRESHOLDS["core_capital_ratio_min"],
        "total_capital_ratio_min": BOU_THRESHOLDS["total_capital_ratio_min"],
        "liquidity_ratio_min": BOU_THRESHOLDS["liquidity_ratio_min"],
        "independent_directors_min": BOU_THRESHOLDS["independent_directors_min"],
    }
    data["compliance_summary"] = {
        "capital_compliant": (
            (inst.core_capital_ratio or 0) >= BOU_THRESHOLDS["core_capital_ratio_min"]
            and (inst.total_capital_ratio or 0) >= BOU_THRESHOLDS["total_capital_ratio_min"]
        ),
        "liquidity_compliant": (
            inst.liquidity_ratio is None
            or inst.tier == "Non-Bank"
            or inst.liquidity_ratio >= BOU_THRESHOLDS["liquidity_ratio_min"]
        ),
        "aml_compliant": inst.aml_compliance_status == "compliant",
        "governance_compliant": (
            inst.independent_directors_count >= BOU_THRESHOLDS["independent_directors_min"]
            and inst.has_internal_auditor
            and inst.has_company_secretary
        ),
    }
    return data


@router.get(
    "/institutions/{institution_code}/reports",
    summary="Compliance report history for a supervised institution",
)
async def get_institution_reports(
    institution_code: str,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    inst = _get_institution_or_404(institution_code, db)
    reports = (
        db.query(ComplianceReport)
        .filter_by(institution_id=inst.id)
        .order_by(ComplianceReport.submitted_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "institution_code": inst.institution_code,
        "institution_name": inst.name,
        "report_count": len(reports),
        "reports": [r.to_dict() for r in reports],
    }


# ─────────────────────────────────────────────────────────────────────────────
# METRICS UPDATE (real-time onsite/offsite data feed)
# ─────────────────────────────────────────────────────────────────────────────

@router.patch(
    "/institutions/{institution_code}/metrics",
    summary="Update live financial metrics for an institution — triggers risk re-score",
)
async def update_institution_metrics(
    institution_code: str,
    payload: InstitutionMetricsUpdate,
    db: Session = Depends(get_db),
):
    """
    Update one or more financial metrics for a supervised institution.
    The compliance engine immediately re-calculates the risk score and
    broadcasts a WebSocket alert if the risk level has changed.

    Typical use cases:
    - Offsite supervision data feed from institution's financial statements
    - BOU on-site examination findings upload
    - AML Unit compliance status update
    """
    inst = _get_institution_or_404(institution_code, db)
    previous_risk_level = inst.risk_level

    updates = payload.model_dump(exclude_none=True)
    for field, value in updates.items():
        if hasattr(inst, field):
            setattr(inst, field, value)

    # If AML compliance status is being updated, refresh the report timestamp
    if "aml_compliance_status" in updates and updates["aml_compliance_status"] == "compliant":
        inst.aml_last_report_date = datetime.now(timezone.utc)

    await _recalculate_and_broadcast(inst, db, "metrics_updated", previous_risk_level)

    logger.info(
        f"📊 Metrics updated: {inst.institution_code} "
        f"| risk: {previous_risk_level} → {inst.risk_level} ({inst.risk_score:.1f}%)"
    )
    return {
        "message": f"Metrics updated for {inst.name}",
        "institution_code": inst.institution_code,
        "new_risk_score": inst.risk_score,
        "new_risk_level": inst.risk_level,
        "previous_risk_level": previous_risk_level,
        "updated_fields": list(updates.keys()),
    }


# ─────────────────────────────────────────────────────────────────────────────
# QUARTERLY COMPLIANCE REPORT SUBMISSION
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/institutions/{institution_code}/compliance-report",
    response_model=ComplianceReportResponse,
    status_code=201,
    summary="Submit quarterly compliance report — updates risk score in real-time",
)
async def submit_compliance_report(
    institution_code: str,
    payload: ComplianceReportCreate,
    db: Session = Depends(get_db),
):
    """
    Submit a periodic compliance report for a supervised institution.
    Mirrors the BOU's offsite surveillance requirement for quarterly financials.

    On submission:
    1. Persists the report snapshot to compliance_reports
    2. Updates the Institution's live metrics from report data
    3. Re-runs compliance risk engine
    4. Broadcasts a WebSocket compliance_alert event to all connected dashboards
    """
    inst = _get_institution_or_404(institution_code, db)
    previous_risk_level = inst.risk_level
    now = datetime.now(timezone.utc)

    # Update institution live metrics from the report
    if payload.paid_up_capital_ugx_bn is not None:
        inst.paid_up_capital_ugx_bn = payload.paid_up_capital_ugx_bn
    if payload.core_capital_ratio is not None:
        inst.core_capital_ratio = payload.core_capital_ratio
    if payload.total_capital_ratio is not None:
        inst.total_capital_ratio = payload.total_capital_ratio
    if payload.liquidity_ratio is not None:
        inst.liquidity_ratio = payload.liquidity_ratio
    if not payload.aml_compliant:
        inst.aml_compliance_status = "non_compliant"
    else:
        inst.aml_compliance_status = "compliant"
        inst.aml_last_report_date = now
    if payload.suspicious_transactions_filed:
        inst.suspicious_tx_count = (inst.suspicious_tx_count or 0) + payload.suspicious_transactions_filed

    # Risk score for this reporting period
    risk_score, risk_level, violations = calculate_compliance_risk(
        inst.to_dict(),
        fraud_stats={
            "fraud_rate": inst.fraud_rate,
            "total_transactions": inst.total_transactions,
            "fraud_transactions": inst.fraud_transactions,
        },
    )

    # Persist the compliance report snapshot
    report = ComplianceReport(
        institution_id=inst.id,
        institution_code=inst.institution_code,
        report_period=payload.report_period,
        report_date=now,
        submitted_by=payload.submitted_by or "BOU Sentinel System",
        paid_up_capital_ugx_bn=payload.paid_up_capital_ugx_bn,
        core_capital_ratio=payload.core_capital_ratio,
        total_capital_ratio=payload.total_capital_ratio,
        liquidity_ratio=payload.liquidity_ratio,
        suspicious_transactions_filed=payload.suspicious_transactions_filed,
        aml_compliant=payload.aml_compliant,
        total_transactions_period=inst.total_transactions,
        flagged_transactions_period=inst.fraud_transactions,
        fraud_rate_period=inst.fraud_rate,
        risk_score=risk_score,
        risk_level=risk_level,
        violations=json.dumps(violations),
    )
    db.add(report)

    # Re-calculate and broadcast
    await _recalculate_and_broadcast(inst, db, "report_submitted", previous_risk_level)
    db.add(report)
    db.commit()
    db.refresh(report)

    logger.info(
        f"📋 Compliance report submitted: {inst.institution_code} "
        f"| period: {payload.report_period} | risk: {risk_level} ({risk_score:.1f}%)"
    )
    return report.to_dict()