"""
BOU Sentinel - Regulatory Institution Models
SQLAlchemy ORM models for tracking regulated institutions and their compliance reports.
All institutions supervised by Bank of Uganda under the Financial Institutions Act 2004 (as amended).
"""
import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Float, Boolean, DateTime, Integer, Text, ForeignKey
)
from sqlalchemy.orm import relationship
from app.database import Base


class Institution(Base):
    """
    Represents a BOU-supervised financial institution.

    Tiers (Financial Institutions Act 2004 + Amendments):
    - Tier I  : Commercial Banks (min capital UGX 150 billion)
    - Tier II : Credit Institutions (min capital UGX 25 billion)
    - Tier III: Microfinance Deposit-Taking Institutions / MDIs (min capital UGX 20 billion)
    - Non-Bank: Forex Bureaux, Money Remitters, Payment Service Providers, Credit Reference Bureaus

    Key regulatory requirements encoded here:
    - Capital Adequacy (Basel II/III): Core ≥8%, Total ≥12%
    - Liquidity: ≥20% of deposit liabilities (FI Liquidity Regulations 2005)
    - AML/CFT: STRs within 2 working days (AML Amendment Act 2017)
    - Governance: ≥4 independent non-executive directors (BOU CG Guidelines 2022)
    """
    __tablename__ = "institutions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_code = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)

    # ── Classification ───────────────────────────────────────────────────────
    tier = Column(String, nullable=False)              # "Tier I", "Tier II", "Tier III", "Non-Bank"
    institution_type = Column(String, nullable=False)  # "Commercial Bank", "Credit Institution", etc.

    # ── License ──────────────────────────────────────────────────────────────
    license_number = Column(String, nullable=True)
    license_status = Column(String, default="active")  # active | suspended | revoked | under_review
    licensed_since = Column(String, nullable=True)     # year string e.g. "1991"

    # ── Capital (UGX billions) — FI Revision of Min Capital Req. Instrument 2022 ──
    paid_up_capital_ugx_bn = Column(Float, nullable=True)
    minimum_capital_required_ugx_bn = Column(Float, nullable=True)
    core_capital_ratio = Column(Float, nullable=True)   # % (Basel II Core, minimum 8%)
    total_capital_ratio = Column(Float, nullable=True)  # % (Basel II Total, minimum 12%)

    # ── Liquidity — FI (Liquidity) Regulations 2005 ──────────────────────────
    liquidity_ratio = Column(Float, nullable=True)     # % of deposit liabilities (minimum 20%)

    # ── AML/CFT — Anti-Money Laundering Act 2013 (as amended) ────────────────
    aml_last_report_date = Column(DateTime(timezone=True), nullable=True)
    aml_compliance_status = Column(String, default="compliant")  # compliant | non_compliant | pending
    suspicious_tx_count = Column(Integer, default=0)    # lifetime STRs filed

    # ── Corporate Governance — BOU CG Guidelines 2022 ────────────────────────
    independent_directors_count = Column(Integer, default=0)
    minimum_directors_required = Column(Integer, default=4)
    has_internal_auditor = Column(Boolean, default=True)
    has_company_secretary = Column(Boolean, default=True)

    # ── Computed Risk Assessment (updated by compliance engine) ──────────────
    risk_score = Column(Float, default=0.0)       # 0.0 – 100.0 %
    risk_level = Column(String, default="low")    # low | medium | high | critical
    compliance_issues = Column(Text, default="[]")  # JSON array of issue strings
    last_risk_updated = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # ── Transaction Stats (derived from BOU Sentinel transaction feed) ────────
    total_transactions = Column(Integer, default=0)
    fraud_transactions = Column(Integer, default=0)
    fraud_rate = Column(Float, default=0.0)        # %

    # ── Location ──────────────────────────────────────────────────────────────
    headquarters = Column(String, default="Kampala")

    # ── Metadata ──────────────────────────────────────────────────────────────
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    compliance_reports = relationship(
        "ComplianceReport", back_populates="institution", cascade="all, delete-orphan"
    )

    def get_issues(self) -> list:
        try:
            if not self.compliance_issues:
                return []
            if isinstance(self.compliance_issues, (str, bytes, bytearray)):
                return json.loads(self.compliance_issues)
            # fallback: attempt to decode string representation
            return json.loads(str(self.compliance_issues))
        except (json.JSONDecodeError, TypeError, ValueError):
            return []

    def set_issues(self, issues: list):
        self.compliance_issues = json.dumps(issues)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "institution_code": self.institution_code,
            "name": self.name,
            "tier": self.tier,
            "institution_type": self.institution_type,
            "license_number": self.license_number,
            "license_status": self.license_status,
            "licensed_since": self.licensed_since,
            # Capital
            "paid_up_capital_ugx_bn": self.paid_up_capital_ugx_bn,
            "minimum_capital_required_ugx_bn": self.minimum_capital_required_ugx_bn,
            "core_capital_ratio": self.core_capital_ratio,
            "total_capital_ratio": self.total_capital_ratio,
            # Liquidity
            "liquidity_ratio": self.liquidity_ratio,
            # AML
            "aml_last_report_date": (
                self.aml_last_report_date.isoformat()
                if self.aml_last_report_date else None
            ),
            "aml_compliance_status": self.aml_compliance_status,
            "suspicious_tx_count": self.suspicious_tx_count,
            # Governance
            "independent_directors_count": self.independent_directors_count,
            "minimum_directors_required": self.minimum_directors_required,
            "has_internal_auditor": self.has_internal_auditor,
            "has_company_secretary": self.has_company_secretary,
            # Risk
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "compliance_issues": self.get_issues(),
            "last_risk_updated": (
                self.last_risk_updated.isoformat()
                if self.last_risk_updated else None
            ),
            # Transaction stats
            "total_transactions": self.total_transactions,
            "fraud_transactions": self.fraud_transactions,
            "fraud_rate": self.fraud_rate,
            # Meta
            "headquarters": self.headquarters,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ComplianceReport(Base):
    """
    Periodic (quarterly) compliance snapshot submitted by or for an institution.
    Captures point-in-time regulatory metrics for audit trail and trend analysis.
    """
    __tablename__ = "compliance_reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id = Column(
        String, ForeignKey("institutions.id"), nullable=False, index=True
    )
    institution_code = Column(String, nullable=False, index=True)

    # ── Report period ─────────────────────────────────────────────────────────
    report_period = Column(String, nullable=False)                 # e.g. "2025-Q2"
    report_date = Column(DateTime(timezone=True), nullable=False)
    submitted_by = Column(String, nullable=True)                   # officer / system

    # ── Capital snapshot ──────────────────────────────────────────────────────
    paid_up_capital_ugx_bn = Column(Float, nullable=True)
    core_capital_ratio = Column(Float, nullable=True)
    total_capital_ratio = Column(Float, nullable=True)

    # ── Liquidity snapshot ────────────────────────────────────────────────────
    liquidity_ratio = Column(Float, nullable=True)

    # ── AML snapshot ──────────────────────────────────────────────────────────
    suspicious_transactions_filed = Column(Integer, default=0)
    aml_compliant = Column(Boolean, default=True)

    # ── Fraud stats from BOU Sentinel ─────────────────────────────────────────
    total_transactions_period = Column(Integer, default=0)
    flagged_transactions_period = Column(Integer, default=0)
    fraud_rate_period = Column(Float, default=0.0)

    # ── Risk result ───────────────────────────────────────────────────────────
    risk_score = Column(Float, default=0.0)
    risk_level = Column(String, default="low")
    violations = Column(Text, default="[]")   # JSON array

    submitted_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    institution = relationship("Institution", back_populates="compliance_reports")

    def to_dict(self) -> dict:
        try:
            if not self.violations:
                violations = []
            elif isinstance(self.violations, (str, bytes, bytearray)):
                violations = json.loads(self.violations)
            else:
                violations = json.loads(str(self.violations))
        except (json.JSONDecodeError, TypeError, ValueError):
            violations = []
        return {
            "id": self.id,
            "institution_id": self.institution_id,
            "institution_code": self.institution_code,
            "report_period": self.report_period,
            "report_date": self.report_date.isoformat() if self.report_date is not None else None,
            "submitted_by": self.submitted_by,
            "paid_up_capital_ugx_bn": self.paid_up_capital_ugx_bn,
            "core_capital_ratio": self.core_capital_ratio,
            "total_capital_ratio": self.total_capital_ratio,
            "liquidity_ratio": self.liquidity_ratio,
            "suspicious_transactions_filed": self.suspicious_transactions_filed,
            "aml_compliant": self.aml_compliant,
            "total_transactions_period": self.total_transactions_period,
            "flagged_transactions_period": self.flagged_transactions_period,
            "fraud_rate_period": self.fraud_rate_period,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "violations": violations,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
        }