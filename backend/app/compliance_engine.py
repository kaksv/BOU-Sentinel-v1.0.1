"""
BOU Sentinel - Regulatory Compliance Risk Engine
Implements Bank of Uganda's supervisory risk-rating methodology.

Legal basis:
  - Financial Institutions Act 2004 (as amended 2016, 2023)
  - FI (Capital Adequacy) Regulations
  - FI (Liquidity) Regulations 2005
  - FI (Revision of Minimum Capital Requirements) Instrument 2022
  - FI (Corporate Governance) Regulations / BOU CG Guidelines 2022
  - Anti-Money Laundering Act 2013 (as amended 2017)
  - AML Amendment Act 2017 — STR within 2 working days
  - Basel II implemented January 2022; Basel III elements ongoing

Uganda removed from FATF grey list: February 2024 (ongoing compliance required).
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("bou-sentinel.compliance")

# ─────────────────────────────────────────────────────────────────────────────
# BOU REGULATORY THRESHOLDS  (exact values from BOU regulations)
# ─────────────────────────────────────────────────────────────────────────────
BOU_THRESHOLDS: Dict[str, Any] = {
    # Capital Adequacy — FI Capital Adequacy Regulations (Basel II/III)
    "core_capital_ratio_min": 8.0,         # % — absolute floor
    "core_capital_ratio_warn": 9.0,        # % — early warning buffer
    "total_capital_ratio_min": 12.0,       # % — absolute floor
    "total_capital_ratio_warn": 13.5,      # % — early warning buffer

    # Minimum Paid-up Capital — FI (Revision of Min Capital Req.) Instrument 2022
    "tier1_min_capital_ugx_bn": 150.0,     # UGX billion — Commercial Banks (deadline June 2024)
    "tier2_min_capital_ugx_bn": 25.0,      # UGX billion — Credit Institutions
    "tier3_min_capital_ugx_bn": 20.0,      # UGX billion — MDIs

    # Liquidity — FI (Liquidity) Regulations 2005
    "liquidity_ratio_min": 20.0,           # % of deposit liabilities (weekly average)
    "liquidity_ratio_warn": 22.0,          # % — early warning

    # AML/CFT — AML Amendment Act 2017
    "str_deadline_working_days": 2,        # STRs must be filed within 2 working days
    "aml_report_review_days": 90,          # BOU reviews AML reporting quarterly
    "aml_report_critical_days": 180,       # >180 days = critical non-compliance

    # Fraud rate thresholds (BOU Sentinel derived)
    "fraud_rate_elevated": 2.0,            # % — elevated but manageable
    "fraud_rate_high": 5.0,                # % — high concern
    "fraud_rate_critical": 15.0,           # % — critical systemic risk

    # Corporate Governance — BOU Consolidated CG Guidelines 2022
    "independent_directors_min": 4,        # minimum independent non-executive directors
}

# Risk component weights (must sum to 1.0)
RISK_WEIGHTS: Dict[str, float] = {
    "capital_adequacy": 0.30,   # 30% — core regulatory requirement
    "liquidity":        0.25,   # 25% — systemic stability indicator
    "aml_cft":          0.20,   # 20% — FATF/FIA compliance
    "fraud":            0.15,   # 15% — BOU Sentinel real-time signal
    "governance":       0.10,   # 10% — BOU CG Guidelines 2022
}

# Minimum capital requirement by tier
TIER_MIN_CAPITAL: Dict[str, Optional[float]] = {
    "Tier I":    BOU_THRESHOLDS["tier1_min_capital_ugx_bn"],
    "Tier II":   BOU_THRESHOLDS["tier2_min_capital_ugx_bn"],
    "Tier III":  BOU_THRESHOLDS["tier3_min_capital_ugx_bn"],
    "Non-Bank":  None,   # no paid-up capital requirement (separate licensing rules)
}


def _parse_date(value: Any) -> Optional[datetime]:
    """Coerce a date value (str, datetime, None) to an aware datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, AttributeError):
            return None
    return None


def calculate_compliance_risk(
    institution_data: Dict[str, Any],
    fraud_stats: Optional[Dict[str, Any]] = None,
) -> Tuple[float, str, List[str]]:
    """
    Calculate BOU compliance risk score for a supervised institution.

    Parameters
    ----------
    institution_data : dict
        Fields from the Institution model (or equivalent dict).
    fraud_stats : dict, optional
        Override fraud metrics (fraud_rate, total_transactions, fraud_transactions).
        If None, values are read from institution_data.

    Returns
    -------
    (risk_score, risk_level, issues)
        risk_score : float 0–100  (percentage)
        risk_level : str "low" | "medium" | "high" | "critical"
        issues     : list[str] sorted by severity
    """
    if fraud_stats is None:
        fraud_stats = {}

    tier = institution_data.get("tier", "Tier I")
    license_status = institution_data.get("license_status", "active")
    issues: List[str] = []
    component_raw: Dict[str, float] = {}   # 0.0 – 1.0 per component

    # ── IMMEDIATE OVERRIDES ───────────────────────────────────────────────────
    if license_status == "revoked":
        return 100.0, "critical", [
            "🔴 CRITICAL: License has been REVOKED by Bank of Uganda — operations must cease"
        ]

    # ── 1. CAPITAL ADEQUACY (weight = 30%) ───────────────────────────────────
    cap = 0.0
    cap_issues: List[str] = []

    paid_up = institution_data.get("paid_up_capital_ugx_bn")
    min_req = institution_data.get("minimum_capital_required_ugx_bn") or TIER_MIN_CAPITAL.get(tier)
    core_r = institution_data.get("core_capital_ratio")
    total_r = institution_data.get("total_capital_ratio")

    # Paid-up capital vs. BOU minimum
    if paid_up is not None and min_req is not None and min_req > 0:
        ratio = paid_up / min_req
        if ratio < 0.50:
            cap = max(cap, 1.0)
            cap_issues.append(
                f"🔴 CRITICAL: Paid-up capital UGX {paid_up:.1f}B is critically below "
                f"UGX {min_req:.0f}B minimum (FI Min Capital Req. Instrument 2022)"
            )
        elif ratio < 0.80:
            cap = max(cap, 0.75)
            cap_issues.append(
                f"🟠 HIGH: Paid-up capital UGX {paid_up:.1f}B significantly below "
                f"UGX {min_req:.0f}B BOU minimum"
            )
        elif ratio < 1.00:
            cap = max(cap, 0.45)
            cap_issues.append(
                f"🟡 WARNING: Paid-up capital UGX {paid_up:.1f}B approaching "
                f"UGX {min_req:.0f}B minimum — compliance at risk"
            )

    # Core capital ratio (Basel II, min 8%)
    if core_r is not None:
        min_c = BOU_THRESHOLDS["core_capital_ratio_min"]
        warn_c = BOU_THRESHOLDS["core_capital_ratio_warn"]
        if core_r < min_c * 0.625:        # < 5%
            cap = max(cap, 1.0)
            cap_issues.append(
                f"🔴 CRITICAL: Core capital ratio {core_r:.1f}% critically below {min_c}% "
                f"BOU/Basel II floor (FI Capital Adequacy Regulations)"
            )
        elif core_r < min_c:              # < 8%
            cap = max(cap, 0.65)
            cap_issues.append(
                f"🟠 NON-COMPLIANT: Core capital ratio {core_r:.1f}% below {min_c}% minimum"
            )
        elif core_r < warn_c:             # 8–9%
            cap = max(cap, 0.25)
            cap_issues.append(
                f"🟡 NOTICE: Core capital ratio {core_r:.1f}% in early warning zone "
                f"(BOU buffer threshold: {warn_c}%)"
            )

    # Total capital ratio (Basel II, min 12%)
    if total_r is not None:
        min_t = BOU_THRESHOLDS["total_capital_ratio_min"]
        warn_t = BOU_THRESHOLDS["total_capital_ratio_warn"]
        if total_r < min_t * 0.67:        # < 8%
            cap = max(cap, 0.90)
            cap_issues.append(
                f"🔴 CRITICAL: Total capital ratio {total_r:.1f}% critically below {min_t}% minimum"
            )
        elif total_r < min_t:             # < 12%
            cap = max(cap, 0.50)
            cap_issues.append(
                f"🟠 NON-COMPLIANT: Total capital ratio {total_r:.1f}% below {min_t}% BOU minimum"
            )
        elif total_r < warn_t:            # 12–13.5%
            cap = max(cap, 0.20)
            cap_issues.append(
                f"🟡 NOTICE: Total capital ratio {total_r:.1f}% below advisory buffer of {warn_t}%"
            )

    component_raw["capital_adequacy"] = cap
    issues.extend(cap_issues)

    # ── 2. LIQUIDITY (weight = 25%) ───────────────────────────────────────────
    liq = 0.0
    liq_r = institution_data.get("liquidity_ratio")
    min_l = BOU_THRESHOLDS["liquidity_ratio_min"]
    warn_l = BOU_THRESHOLDS["liquidity_ratio_warn"]

    if liq_r is not None and tier != "Non-Bank":
        if liq_r < min_l * 0.50:         # < 10%
            liq = 1.0
            issues.append(
                f"🔴 CRITICAL: Liquidity ratio {liq_r:.1f}% critically below {min_l}% "
                f"BOU floor — imminent solvency risk (FI Liquidity Regulations 2005)"
            )
        elif liq_r < min_l * 0.75:       # < 15%
            liq = 0.75
            issues.append(
                f"🟠 HIGH: Liquidity ratio {liq_r:.1f}% dangerously below {min_l}% minimum"
            )
        elif liq_r < min_l:              # < 20%
            liq = 0.50
            issues.append(
                f"🟠 NON-COMPLIANT: Liquidity ratio {liq_r:.1f}% below {min_l}% BOU minimum "
                f"(FI Liquidity Regulations 2005 — prompt corrective action required)"
            )
        elif liq_r < warn_l:             # 20–22%
            liq = 0.15
            issues.append(
                f"🟡 NOTICE: Liquidity ratio {liq_r:.1f}% within early warning band "
                f"({min_l}–{warn_l}%)"
            )

    component_raw["liquidity"] = liq

    # ── 3. AML/CFT COMPLIANCE (weight = 20%) ─────────────────────────────────
    aml = 0.0
    aml_status = institution_data.get("aml_compliance_status", "compliant")
    aml_date = _parse_date(institution_data.get("aml_last_report_date"))

    if aml_status == "non_compliant":
        aml = max(aml, 0.90)
        issues.append(
            "🔴 CRITICAL: Institution flagged AML/CFT NON-COMPLIANT by FIA "
            "(Anti-Money Laundering Act 2013 as amended)"
        )
    elif aml_status == "pending":
        aml = max(aml, 0.35)
        issues.append(
            "🟡 PENDING: AML/CFT compliance status unconfirmed — submission awaited"
        )

    if aml_date is None:
        aml = max(aml, 0.65)
        issues.append(
            "🟠 WARNING: No Suspicious Transaction Report (STR) on record "
            "(AML Amendment Act 2017 — STRs required within 2 working days)"
        )
    else:
        days = (datetime.now(timezone.utc) - aml_date).days
        crit = BOU_THRESHOLDS["aml_report_critical_days"]
        review = BOU_THRESHOLDS["aml_report_review_days"]
        if days > crit:
            aml = max(aml, 0.85)
            issues.append(
                f"🔴 CRITICAL: AML report {days} days old — overdue by {days - review} days "
                f"(BOU requires quarterly AML/STR review)"
            )
        elif days > review:
            aml = max(aml, 0.55)
            issues.append(
                f"🟠 OVERDUE: AML/STR report {days} days old — {days - review} days overdue"
            )
        elif days > review * 0.8:
            aml = max(aml, 0.15)
            issues.append(
                f"🟡 NOTICE: AML/STR report {days} days old — approaching {review}-day review cycle"
            )

    component_raw["aml_cft"] = aml

    # ── 4. FRAUD RATE (weight = 15%) — BOU Sentinel signal ───────────────────
    fraud = 0.0
    fraud_rate = fraud_stats.get(
        "fraud_rate", institution_data.get("fraud_rate", 0.0)
    ) or 0.0
    total_tx = fraud_stats.get(
        "total_transactions", institution_data.get("total_transactions", 0)
    ) or 0
    fraud_tx = fraud_stats.get(
        "fraud_transactions", institution_data.get("fraud_transactions", 0)
    ) or 0

    crit_f = BOU_THRESHOLDS["fraud_rate_critical"]
    high_f = BOU_THRESHOLDS["fraud_rate_high"]
    elev_f = BOU_THRESHOLDS["fraud_rate_elevated"]

    if fraud_rate > crit_f:
        fraud = 1.0
        issues.append(
            f"🔴 CRITICAL: Fraud rate {fraud_rate:.1f}% exceeds {crit_f}% critical threshold "
            f"({fraud_tx}/{total_tx} transactions flagged by BOU Sentinel AI)"
        )
    elif fraud_rate > high_f:
        fraud = 0.65
        issues.append(
            f"🟠 HIGH: Fraud rate {fraud_rate:.1f}% — {fraud_tx} flagged transactions "
            f"in BOU Sentinel (threshold: {high_f}%)"
        )
    elif fraud_rate > elev_f:
        fraud = 0.35
        issues.append(
            f"🟡 ELEVATED: Fraud rate {fraud_rate:.1f}% above normal baseline "
            f"({fraud_tx}/{total_tx} in Sentinel — monitoring required)"
        )
    elif total_tx > 0 and fraud_tx > 0:
        issues.append(
            f"ℹ️  INFO: {fraud_tx} flagged transaction(s) out of {total_tx} "
            f"monitored by BOU Sentinel"
        )

    component_raw["fraud"] = fraud

    # ── 5. CORPORATE GOVERNANCE (weight = 10%) — BOU CG Guidelines 2022 ──────
    gov = 0.0
    directors = institution_data.get("independent_directors_count", 0) or 0
    min_dir = BOU_THRESHOLDS["independent_directors_min"]

    if directors < min_dir:
        shortfall = min_dir - directors
        gov = max(gov, min(1.0, shortfall / min_dir))
        issues.append(
            f"🟠 WARNING: {directors} independent director(s) — {shortfall} below BOU minimum "
            f"of {min_dir} (BOU Consolidated CG Guidelines 2022)"
        )

    if not institution_data.get("has_internal_auditor", True):
        gov = max(gov, 0.50)
        issues.append(
            "🟠 WARNING: No qualified internal auditor appointed "
            "(Financial Institutions Act 2004, s. requirement)"
        )

    if not institution_data.get("has_company_secretary", True):
        gov = max(gov, 0.30)
        issues.append(
            "🟡 NOTICE: No BOU-approved company secretary on record "
            "(BOU CG Guidelines 2022 — in-house secretary required)"
        )

    component_raw["governance"] = gov

    # ── LICENSE STATUS ADJUSTMENTS ────────────────────────────────────────────
    if license_status == "suspended":
        component_raw["capital_adequacy"] = max(
            component_raw.get("capital_adequacy", 0.0), 0.85
        )
        issues.insert(0, "🔴 CRITICAL: License SUSPENDED by Bank of Uganda — immediate action required")
    elif license_status == "under_review":
        # Elevate AML and governance risk floors during supervisory review
        component_raw["aml_cft"] = max(component_raw.get("aml_cft", 0.0), 0.40)
        issues.insert(0, "🟠 WARNING: License under active BOU supervisory review")

    # ── WEIGHTED AGGREGATION ──────────────────────────────────────────────────
    raw = sum(component_raw.get(k, 0.0) * w for k, w in RISK_WEIGHTS.items())
    risk_score = round(min(100.0, raw * 100.0), 2)

    # ── RISK LEVEL CLASSIFICATION ─────────────────────────────────────────────
    if risk_score >= 70 or license_status in ("suspended", "revoked"):
        risk_level = "critical"
    elif risk_score >= 40:
        risk_level = "high"
    elif risk_score >= 18:
        risk_level = "medium"
    else:
        risk_level = "low"

    return risk_score, risk_level, issues


def build_regulatory_summary(institutions: list) -> Dict[str, Any]:
    """
    Aggregate regulatory statistics across all supervised institutions.
    Used for the BOU regulator dashboard.
    """
    total = len(institutions)
    if total == 0:
        return {
            "total_institutions": 0,
            "by_risk_level": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "by_tier": {},
            "non_compliant_count": 0,
            "suspended_count": 0,
            "average_risk_score": 0.0,
            "liquidity_non_compliant": 0,
            "capital_non_compliant": 0,
            "aml_non_compliant": 0,
        }

    risk_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    tier_counts: Dict[str, int] = {}
    risk_scores = []
    liquidity_nc = capital_nc = aml_nc = suspended = 0

    for inst in institutions:
        d = inst if isinstance(inst, dict) else inst.to_dict()
        level = d.get("risk_level", "low")
        risk_counts[level] = risk_counts.get(level, 0) + 1
        tier = d.get("tier", "Unknown")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        risk_scores.append(d.get("risk_score", 0.0))

        # Liquidity non-compliance
        liq = d.get("liquidity_ratio")
        if liq is not None and d.get("tier") != "Non-Bank" and liq < BOU_THRESHOLDS["liquidity_ratio_min"]:
            liquidity_nc += 1

        # Capital non-compliance
        paid = d.get("paid_up_capital_ugx_bn")
        min_r = d.get("minimum_capital_required_ugx_bn")
        core = d.get("core_capital_ratio")
        if (paid is not None and min_r is not None and paid < min_r) or \
           (core is not None and core < BOU_THRESHOLDS["core_capital_ratio_min"]):
            capital_nc += 1

        # AML non-compliance
        if d.get("aml_compliance_status") in ("non_compliant", "pending"):
            aml_nc += 1

        if d.get("license_status") == "suspended":
            suspended += 1

    avg_risk = round(sum(risk_scores) / len(risk_scores), 2) if risk_scores else 0.0
    non_compliant = risk_counts["critical"] + risk_counts["high"]

    return {
        "total_institutions": total,
        "by_risk_level": risk_counts,
        "by_tier": tier_counts,
        "non_compliant_count": non_compliant,
        "suspended_count": suspended,
        "average_risk_score": avg_risk,
        "liquidity_non_compliant": liquidity_nc,
        "capital_non_compliant": capital_nc,
        "aml_non_compliant": aml_nc,
        "compliance_rate_pct": round(
            (total - non_compliant) / total * 100, 1
        ) if total > 0 else 100.0,
    }