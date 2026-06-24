"""
BOU Sentinel - Regulatory Compliance Schemas
Pydantic v2 models for regulatory API request/response validation.
"""
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# INSTITUTION SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class InstitutionMetricsUpdate(BaseModel):
    """PATCH /api/regulatory/institutions/{code}/metrics — update live financial metrics."""
    paid_up_capital_ugx_bn: Optional[float] = None
    core_capital_ratio: Optional[float] = None
    total_capital_ratio: Optional[float] = None
    liquidity_ratio: Optional[float] = None
    aml_compliance_status: Optional[str] = None          # compliant | non_compliant | pending
    independent_directors_count: Optional[int] = None
    has_internal_auditor: Optional[bool] = None
    has_company_secretary: Optional[bool] = None
    license_status: Optional[str] = None                 # active | suspended | revoked | under_review
    suspicious_tx_count: Optional[int] = None


class InstitutionResponse(BaseModel):
    """Full institution detail including computed risk score."""
    id: str
    institution_code: str
    name: str
    tier: str
    institution_type: str
    license_number: Optional[str] = None
    license_status: str
    licensed_since: Optional[str] = None
    # Capital
    paid_up_capital_ugx_bn: Optional[float] = None
    minimum_capital_required_ugx_bn: Optional[float] = None
    core_capital_ratio: Optional[float] = None
    total_capital_ratio: Optional[float] = None
    # Liquidity
    liquidity_ratio: Optional[float] = None
    # AML
    aml_last_report_date: Optional[str] = None
    aml_compliance_status: str
    suspicious_tx_count: int
    # Governance
    independent_directors_count: int
    minimum_directors_required: int
    has_internal_auditor: bool
    has_company_secretary: bool
    # Risk
    risk_score: float
    risk_level: str
    compliance_issues: List[str]
    last_risk_updated: Optional[str] = None
    # Transaction stats
    total_transactions: int
    fraud_transactions: int
    fraud_rate: float
    # Meta
    headquarters: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class InstitutionListItem(BaseModel):
    """Compact institution summary for list / dashboard views."""
    institution_code: str
    name: str
    tier: str
    institution_type: str
    license_status: str
    risk_score: float
    risk_level: str
    liquidity_ratio: Optional[float] = None
    core_capital_ratio: Optional[float] = None
    aml_compliance_status: str
    fraud_rate: float
    total_transactions: int
    fraud_transactions: int
    compliance_issues_count: int
    last_risk_updated: Optional[str] = None

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# COMPLIANCE REPORT SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class ComplianceReportCreate(BaseModel):
    """POST /api/regulatory/institutions/{code}/compliance-report"""
    report_period: str = Field(
        ...,
        description="Reporting period, e.g. '2025-Q2'",
        examples=["2025-Q2"],
    )
    submitted_by: Optional[str] = Field(None, description="Name of submitting officer")
    # Capital
    paid_up_capital_ugx_bn: Optional[float] = None
    core_capital_ratio: Optional[float] = None
    total_capital_ratio: Optional[float] = None
    # Liquidity
    liquidity_ratio: Optional[float] = None
    # AML
    suspicious_transactions_filed: int = Field(0, ge=0)
    aml_compliant: bool = True


class ComplianceReportResponse(BaseModel):
    id: str
    institution_id: str
    institution_code: str
    report_period: str
    report_date: Optional[str] = None
    submitted_by: Optional[str] = None
    paid_up_capital_ugx_bn: Optional[float] = None
    core_capital_ratio: Optional[float] = None
    total_capital_ratio: Optional[float] = None
    liquidity_ratio: Optional[float] = None
    suspicious_transactions_filed: int
    aml_compliant: bool
    total_transactions_period: int
    flagged_transactions_period: int
    fraud_rate_period: float
    risk_score: float
    risk_level: str
    violations: List[str]
    submitted_at: Optional[str] = None

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD / SUMMARY SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class RegulatoryDashboardResponse(BaseModel):
    """GET /api/regulatory/summary — regulator overview dashboard."""
    total_institutions: int
    by_risk_level: Dict[str, int]
    by_tier: Dict[str, int]
    non_compliant_count: int
    suspended_count: int
    average_risk_score: float
    liquidity_non_compliant: int
    capital_non_compliant: int
    aml_non_compliant: int
    compliance_rate_pct: float
    top_risk_institutions: List[Dict[str, Any]]
    ws_connected_clients: int
    generated_at: str


class RegulatoryAlertEvent(BaseModel):
    """
    WebSocket broadcast payload emitted when an institution's risk changes.
    Frontend subscribes to the same /ws endpoint and filters by type.
    """
    type: str = "compliance_alert"
    institution_code: str
    institution_name: str
    risk_score: float
    risk_level: str
    previous_risk_level: Optional[str] = None
    trigger: str           # "fraud_detected" | "metrics_updated" | "report_submitted"
    issues: List[str]
    timestamp: str