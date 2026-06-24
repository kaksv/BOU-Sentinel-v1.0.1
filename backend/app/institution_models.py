"""
BOU Sentinel - Regulated Institution Models
Tracks all institutions supervised by the Bank of Uganda across all tiers.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Boolean, DateTime, Integer, Text, Enum
from app.database import Base
import enum


class InstitutionTier(str, enum.Enum):
    TIER_1 = "tier_1"         # Commercial Banks
    TIER_2 = "tier_2"         # Credit Institutions
    TIER_3 = "tier_3"         # Microfinance Deposit-Taking Institutions (MDIs)
    TIER_4 = "tier_4"         # Large SACCOs
    FOREX_BUREAU = "forex_bureau"
    MONEY_REMITTER = "money_remitter"
    PAYMENT_PROVIDER = "payment_provider"
    CREDIT_REFERENCE = "credit_reference"


class ComplianceStatus(str, enum.Enum):
    COMPLIANT = "compliant"
    WARNING = "warning"
    NON_COMPLIANT = "non_compliant"
    UNDER_REVIEW = "under_review"
    SUSPENDED = "suspended"


class RegulatedInstitution(Base):
    __tablename__ = "regulated_institutions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_code = Column(String, unique=True, nullable=False, index=True)
    institution_name = Column(String, nullable=False)
    tier = Column(String, nullable=False)               # InstitutionTier enum value
    license_number = Column(String, nullable=True)
    license_issue_date = Column(DateTime(timezone=True), nullable=True)
    license_expiry_date = Column(DateTime(timezone=True), nullable=True)
    registered_address = Column(String, nullable=True)
    region = Column(String, nullable=True)              # Kampala, Entebbe, Jinja etc.
    contact_email = Column(String, nullable=True)
    primary_regulator = Column(String, default="Bank of Uganda")

    # Capital requirements (in UGX millions)
    minimum_capital_required = Column(Float, nullable=True)   # e.g. 150,000 (UGX 150B for Tier 1)
    paid_up_capital = Column(Float, nullable=True)            # reported capital
    capital_adequacy_ratio = Column(Float, nullable=True)     # CAR % (min 8% core, 12% total)
    core_capital_ratio = Column(Float, nullable=True)         # must be >= 8%
    total_capital_ratio = Column(Float, nullable=True)        # must be >= 12%
    liquidity_ratio = Column(Float, nullable=True)            # must be >= 20% (liquid assets/demand liabilities)

    # AML/CFT compliance fields
    aml_policy_submitted = Column(Boolean, default=False)
    cdd_procedures_compliant = Column(Boolean, default=False)
    str_submitted_last_quarter = Column(Boolean, default=False)  # Suspicious Transaction Reports
    aml_audit_report_current = Column(Boolean, default=False)
    fatf_compliance_score = Column(Float, default=0.0)          # 0-100

    # Reporting compliance
    quarterly_returns_current = Column(Boolean, default=True)
    annual_returns_submitted = Column(Boolean, default=True)
    last_inspection_date = Column(DateTime(timezone=True), nullable=True)
    next_inspection_due = Column(DateTime(timezone=True), nullable=True)
    outstanding_reports = Column(Integer, default=0)

    # Corporate governance
    board_compliant = Column(Boolean, default=True)             # >= 4 independent non-exec directors
    ceo_approved = Column(Boolean, default=True)
    company_secretary_approved = Column(Boolean, default=True)
    governance_score = Column(Float, default=100.0)             # 0-100

    # Risk & compliance scoring
    overall_risk_score = Column(Float, default=0.0)             # 0-100 (higher = riskier)
    compliance_score = Column(Float, default=100.0)             # 0-100 (higher = better)
    compliance_status = Column(String, default=ComplianceStatus.COMPLIANT)
    risk_flags = Column(Text, nullable=True)                    # JSON list of active risk flags

    # Deposit Protection Fund
    dpf_contribution_current = Column(Boolean, default=True)    # 0.2% of avg weighted deposit liabilities
    deposit_protection_fund_id = Column(String, nullable=True)

    # Transaction monitoring (linked to fraud detection)
    total_transactions_30d = Column(Integer, default=0)
    flagged_transactions_30d = Column(Integer, default=0)
    fraud_rate_30d = Column(Float, default=0.0)                 # %
    high_risk_transaction_volume = Column(Float, default=0.0)   # UGX

    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "institution_code": self.institution_code,
            "institution_name": self.institution_name,
            "tier": self.tier,
            "license_number": self.license_number,
            "license_issue_date": self.license_issue_date.isoformat() if self.license_issue_date else None,
            "license_expiry_date": self.license_expiry_date.isoformat() if self.license_expiry_date else None,
            "registered_address": self.registered_address,
            "region": self.region,
            "primary_regulator": self.primary_regulator,
            "minimum_capital_required": self.minimum_capital_required,
            "paid_up_capital": self.paid_up_capital,
            "capital_adequacy_ratio": self.capital_adequacy_ratio,
            "core_capital_ratio": self.core_capital_ratio,
            "total_capital_ratio": self.total_capital_ratio,
            "liquidity_ratio": self.liquidity_ratio,
            "aml_policy_submitted": self.aml_policy_submitted,
            "cdd_procedures_compliant": self.cdd_procedures_compliant,
            "str_submitted_last_quarter": self.str_submitted_last_quarter,
            "aml_audit_report_current": self.aml_audit_report_current,
            "fatf_compliance_score": self.fatf_compliance_score,
            "quarterly_returns_current": self.quarterly_returns_current,
            "annual_returns_submitted": self.annual_returns_submitted,
            "last_inspection_date": self.last_inspection_date.isoformat() if self.last_inspection_date else None,
            "next_inspection_due": self.next_inspection_due.isoformat() if self.next_inspection_due else None,
            "outstanding_reports": self.outstanding_reports,
            "board_compliant": self.board_compliant,
            "ceo_approved": self.ceo_approved,
            "company_secretary_approved": self.company_secretary_approved,
            "governance_score": self.governance_score,
            "overall_risk_score": self.overall_risk_score,
            "compliance_score": self.compliance_score,
            "compliance_status": self.compliance_status,
            "risk_flags": self.risk_flags,
            "dpf_contribution_current": self.dpf_contribution_current,
            "total_transactions_30d": self.total_transactions_30d,
            "flagged_transactions_30d": self.flagged_transactions_30d,
            "fraud_rate_30d": self.fraud_rate_30d,
            "high_risk_transaction_volume": self.high_risk_transaction_volume,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }