"""
BOU Sentinel - Institution Compliance Engine
Seeds & manages all BOU-regulated institutions with real compliance scoring.
"""
import json
import logging
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("bou-sentinel.institutions")


# =====================================================================
# BOU Regulatory Thresholds (Financial Institutions Act 2004 / Amended)
# =====================================================================
BOU_THRESHOLDS = {
    "tier_1": {
        "name": "Commercial Banks",
        "min_capital_ugx_millions": 150_000,   # UGX 150 billion (2022 instrument)
        "core_capital_ratio_min": 8.0,          # % of risk-adjusted assets
        "total_capital_ratio_min": 12.0,        # %
        "liquidity_ratio_min": 20.0,            # % of demand+time liabilities
        "dpf_contribution_rate": 0.2,           # % of average weighted deposit liabilities
        "governing_law": "Financial Institutions Act 2004 (Amended 2016, 2023)",
    },
    "tier_2": {
        "name": "Credit Institutions",
        "min_capital_ugx_millions": 25_000,    # UGX 25 billion
        "core_capital_ratio_min": 8.0,
        "total_capital_ratio_min": 12.0,
        "liquidity_ratio_min": 15.0,
        "dpf_contribution_rate": 0.2,
        "governing_law": "Financial Institutions Act 2004",
    },
    "tier_3": {
        "name": "Microfinance Deposit-Taking Institutions (MDIs)",
        "min_capital_ugx_millions": 20_000,    # UGX 20 billion
        "core_capital_ratio_min": 8.0,
        "total_capital_ratio_min": 12.0,
        "liquidity_ratio_min": 15.0,
        "dpf_contribution_rate": 0.2,
        "governing_law": "MDI Act 2003 (Amended 2023)",
    },
    "tier_4": {
        "name": "Large SACCOs",
        "min_capital_ugx_millions": 500,
        "core_capital_ratio_min": 5.0,
        "total_capital_ratio_min": 8.0,
        "liquidity_ratio_min": 10.0,
        "dpf_contribution_rate": 0.0,
        "governing_law": "Cooperatives Societies Act / UMRA oversight",
    },
    "forex_bureau": {
        "name": "Forex Bureaus",
        "min_capital_ugx_millions": 50,
        "core_capital_ratio_min": 0,
        "total_capital_ratio_min": 0,
        "liquidity_ratio_min": 0,
        "dpf_contribution_rate": 0.0,
        "governing_law": "Foreign Exchange Act 2004 / BOU Guidelines 2018",
    },
    "money_remitter": {
        "name": "Money Remitters",
        "min_capital_ugx_millions": 200,
        "core_capital_ratio_min": 0,
        "total_capital_ratio_min": 0,
        "liquidity_ratio_min": 0,
        "dpf_contribution_rate": 0.0,
        "governing_law": "National Payment Systems Act 2020",
    },
    "payment_provider": {
        "name": "Non-Bank Payment Service Providers",
        "min_capital_ugx_millions": 100,
        "core_capital_ratio_min": 0,
        "total_capital_ratio_min": 0,
        "liquidity_ratio_min": 0,
        "dpf_contribution_rate": 0.0,
        "governing_law": "National Payment Systems Act 2020",
    },
    "credit_reference": {
        "name": "Credit Reference Bureaus",
        "min_capital_ugx_millions": 500,
        "core_capital_ratio_min": 0,
        "total_capital_ratio_min": 0,
        "liquidity_ratio_min": 0,
        "dpf_contribution_rate": 0.0,
        "governing_law": "Financial Institutions (Credit Reference Bureau) Regulations 2022",
    },
}

# =====================================================================
# Real BOU-Regulated Institutions Seed Data
# =====================================================================
SEED_INSTITUTIONS = [
    # ---- TIER 1: COMMERCIAL BANKS ----
    {
        "institution_code": "STB-001", "institution_name": "Stanbic Bank Uganda Limited",
        "tier": "tier_1", "license_number": "BOU/FI/001", "region": "Kampala",
        "registered_address": "Crested Towers, Hannington Road, Kampala",
        "paid_up_capital": 178_000, "compliance_profile": "strong",
    },
    {
        "institution_code": "CTB-002", "institution_name": "Centenary Rural Development Bank Limited",
        "tier": "tier_1", "license_number": "BOU/FI/002", "region": "Kampala",
        "registered_address": "Mapeera House, Ben Kiwanuka Street, Kampala",
        "paid_up_capital": 165_000, "compliance_profile": "strong",
    },
    {
        "institution_code": "ABSA-003", "institution_name": "Absa Bank Uganda Limited",
        "tier": "tier_1", "license_number": "BOU/FI/003", "region": "Kampala",
        "registered_address": "Barclays House, Hannington Road, Kampala",
        "paid_up_capital": 155_000, "compliance_profile": "strong",
    },
    {
        "institution_code": "SCB-004", "institution_name": "Standard Chartered Bank Uganda Limited",
        "tier": "tier_1", "license_number": "BOU/FI/004", "region": "Kampala",
        "registered_address": "Plot 5, Speke Road, Kampala",
        "paid_up_capital": 162_000, "compliance_profile": "strong",
    },
    {
        "institution_code": "DFCU-005", "institution_name": "DFCU Bank Limited",
        "tier": "tier_1", "license_number": "BOU/FI/005", "region": "Kampala",
        "registered_address": "Plot 26, Kyadondo Road, Nakasero, Kampala",
        "paid_up_capital": 153_000, "compliance_profile": "moderate",
    },
    {
        "institution_code": "EQB-006", "institution_name": "Equity Bank Uganda Limited",
        "tier": "tier_1", "license_number": "BOU/FI/006", "region": "Kampala",
        "registered_address": "Plot 73, Kampala Road, Kampala",
        "paid_up_capital": 158_000, "compliance_profile": "strong",
    },
    {
        "institution_code": "DTB-007", "institution_name": "Diamond Trust Bank Uganda Limited",
        "tier": "tier_1", "license_number": "BOU/FI/007", "region": "Kampala",
        "registered_address": "17/19 Kampala Road, Kampala",
        "paid_up_capital": 151_000, "compliance_profile": "moderate",
    },
    {
        "institution_code": "KCB-008", "institution_name": "KCB Bank Uganda Limited",
        "tier": "tier_1", "license_number": "BOU/FI/008", "region": "Kampala",
        "registered_address": "Plot 1, Pilkington Road, Kampala",
        "paid_up_capital": 154_000, "compliance_profile": "strong",
    },
    {
        "institution_code": "BOA-009", "institution_name": "Bank of Africa Uganda Limited",
        "tier": "tier_1", "license_number": "BOU/FI/009", "region": "Kampala",
        "registered_address": "Plot 45, Jinja Road, Kampala",
        "paid_up_capital": 152_000, "compliance_profile": "moderate",
    },
    {
        "institution_code": "HFB-010", "institution_name": "Housing Finance Bank Limited",
        "tier": "tier_1", "license_number": "BOU/FI/010", "region": "Kampala",
        "registered_address": "Investment House, Plot 4 Wampewo Ave, Kampala",
        "paid_up_capital": 150_500, "compliance_profile": "moderate",
    },
    {
        "institution_code": "ECO-011", "institution_name": "Ecobank Uganda Limited",
        "tier": "tier_1", "license_number": "BOU/FI/011", "region": "Kampala",
        "registered_address": "Plot 4, Parliament Avenue, Kampala",
        "paid_up_capital": 151_200, "compliance_profile": "moderate",
    },
    {
        "institution_code": "UBA-012", "institution_name": "United Bank for Africa Uganda Limited",
        "tier": "tier_1", "license_number": "BOU/FI/012", "region": "Kampala",
        "registered_address": "Plot 2, Jinja Road, Kampala",
        "paid_up_capital": 150_800, "compliance_profile": "moderate",
    },
    {
        "institution_code": "BOB-013", "institution_name": "Bank of Baroda Uganda Limited",
        "tier": "tier_1", "license_number": "BOU/FI/013", "region": "Kampala",
        "registered_address": "Plot 18, Kampala Road, Kampala",
        "paid_up_capital": 158_000, "compliance_profile": "strong",
    },
    {
        "institution_code": "IMB-014", "institution_name": "I&M Bank Uganda Limited",
        "tier": "tier_1", "license_number": "BOU/FI/014", "region": "Kampala",
        "registered_address": "Plot 6, Hannington Road, Kampala",
        "paid_up_capital": 152_500, "compliance_profile": "moderate",
    },
    {
        "institution_code": "GTB-015", "institution_name": "Guaranty Trust Bank Uganda Limited",
        "tier": "tier_1", "license_number": "BOU/FI/015", "region": "Kampala",
        "registered_address": "Plot 56, Kampala Road, Kampala",
        "paid_up_capital": 151_000, "compliance_profile": "at_risk",
    },
    {
        "institution_code": "EXIM-016", "institution_name": "Exim Bank Uganda Limited",
        "tier": "tier_1", "license_number": "BOU/FI/016", "region": "Kampala",
        "registered_address": "Plot 6, Colville Street, Kampala",
        "paid_up_capital": 148_000, "compliance_profile": "at_risk",  # below threshold
    },
    {
        "institution_code": "NCBA-017", "institution_name": "NCBA Bank Uganda Limited",
        "tier": "tier_1", "license_number": "BOU/FI/017", "region": "Kampala",
        "registered_address": "Plot 7, Hannington Road, Kampala",
        "paid_up_capital": 150_200, "compliance_profile": "moderate",
    },
    {
        "institution_code": "SLM-018", "institution_name": "Salaam Bank Uganda Limited",
        "tier": "tier_1", "license_number": "BOU/FI/018", "region": "Kampala",
        "registered_address": "Plot 23, Lugogo One Building, Lugogo Bypass, Kampala",
        "paid_up_capital": 150_100, "compliance_profile": "moderate",
    },
    {
        "institution_code": "CBU-019", "institution_name": "Cairo International Bank Limited",
        "tier": "tier_1", "license_number": "BOU/FI/019", "region": "Kampala",
        "registered_address": "Plot 6A, Windsor Loop, Kampala",
        "paid_up_capital": 149_000, "compliance_profile": "at_risk",  # near threshold
    },
    {
        "institution_code": "FTB-020", "institution_name": "Finance Trust Bank Limited",
        "tier": "tier_1", "license_number": "BOU/FI/020", "region": "Kampala",
        "registered_address": "Plot 115/117, Katwe, Kampala",
        "paid_up_capital": 150_300, "compliance_profile": "moderate",
    },
    # ---- TIER 2: CREDIT INSTITUTIONS ----
    {
        "institution_code": "BRC-101", "institution_name": "BRAC Uganda Bank Limited",
        "tier": "tier_2", "license_number": "BOU/CI/001", "region": "Kampala",
        "registered_address": "Plot 1, Luthuli Avenue, Bugolobi, Kampala",
        "paid_up_capital": 28_000, "compliance_profile": "strong",
    },
    {
        "institution_code": "OPP-102", "institution_name": "Opportunity Bank Uganda Limited",
        "tier": "tier_2", "license_number": "BOU/CI/002", "region": "Kampala",
        "registered_address": "Plot 1B, Opp. Clock Tower, Ben Kiwanuka St, Kampala",
        "paid_up_capital": 26_500, "compliance_profile": "moderate",
    },
    {
        "institution_code": "TOP-103", "institution_name": "Top Finance Bank Limited",
        "tier": "tier_2", "license_number": "BOU/CI/003", "region": "Kampala",
        "registered_address": "Plot 28, William Street, Kampala",
        "paid_up_capital": 24_000, "compliance_profile": "at_risk",
    },
    {
        "institution_code": "YAK-104", "institution_name": "Yako Bank Uganda Limited",
        "tier": "tier_2", "license_number": "BOU/CI/004", "region": "Kampala",
        "registered_address": "Plot 2, Luwum Street, Kampala",
        "paid_up_capital": 22_000, "compliance_profile": "at_risk",
    },
    # ---- TIER 3: MDIs ----
    {
        "institution_code": "FNC-201", "institution_name": "FINCA Uganda Limited (MDI)",
        "tier": "tier_3", "license_number": "BOU/MDI/001", "region": "Kampala",
        "registered_address": "Plot 11A, Acacia Avenue, Kololo, Kampala",
        "paid_up_capital": 22_000, "compliance_profile": "strong",
    },
    {
        "institution_code": "PRD-202", "institution_name": "PRIDE Microfinance Limited (MDI)",
        "tier": "tier_3", "license_number": "BOU/MDI/002", "region": "Kampala",
        "registered_address": "Plot 14, Nkrumah Road, Kampala",
        "paid_up_capital": 21_500, "compliance_profile": "moderate",
    },
    {
        "institution_code": "UGA-203", "institution_name": "UGAFODE Microfinance Limited (MDI)",
        "tier": "tier_3", "license_number": "BOU/MDI/003", "region": "Kampala",
        "registered_address": "Plot 22B, Entebbe Road, Kampala",
        "paid_up_capital": 20_500, "compliance_profile": "moderate",
    },
    # ---- FOREX BUREAUS (sample) ----
    {
        "institution_code": "FXB-301", "institution_name": "Pearl Forex Bureau Limited",
        "tier": "forex_bureau", "license_number": "BOU/FX/001", "region": "Kampala",
        "registered_address": "Plot 3, Kampala Road, Kampala",
        "paid_up_capital": 55, "compliance_profile": "strong",
    },
    {
        "institution_code": "FXB-302", "institution_name": "Nile Forex Bureau Limited",
        "tier": "forex_bureau", "license_number": "BOU/FX/002", "region": "Jinja",
        "registered_address": "Plot 14, Main Street, Jinja",
        "paid_up_capital": 52, "compliance_profile": "moderate",
    },
    {
        "institution_code": "FXB-303", "institution_name": "Crane Forex Bureau Limited",
        "tier": "forex_bureau", "license_number": "BOU/FX/003", "region": "Kampala",
        "registered_address": "Kampala Road, Kampala",
        "paid_up_capital": 48, "compliance_profile": "at_risk",
    },
    # ---- MONEY REMITTERS ----
    {
        "institution_code": "MR-401", "institution_name": "Western Union Uganda (MTN Partnership)",
        "tier": "money_remitter", "license_number": "BOU/MR/001", "region": "Kampala",
        "registered_address": "Kampala Business Park, Kampala",
        "paid_up_capital": 210, "compliance_profile": "strong",
    },
    {
        "institution_code": "MR-402", "institution_name": "MoneyGram Uganda Limited",
        "tier": "money_remitter", "license_number": "BOU/MR/002", "region": "Kampala",
        "registered_address": "Plot 18, Kampala Road, Kampala",
        "paid_up_capital": 205, "compliance_profile": "strong",
    },
    # ---- NON-BANK PAYMENT SERVICE PROVIDERS ----
    {
        "institution_code": "PSP-501", "institution_name": "MTN Mobile Money Uganda Limited",
        "tier": "payment_provider", "license_number": "BOU/PSP/001", "region": "Kampala",
        "registered_address": "MTN Towers, Hannington Road, Kampala",
        "paid_up_capital": 350, "compliance_profile": "strong",
    },
    {
        "institution_code": "PSP-502", "institution_name": "Airtel Money Uganda Limited",
        "tier": "payment_provider", "license_number": "BOU/PSP/002", "region": "Kampala",
        "registered_address": "Plot 7, Ntinda Industrial Area, Kampala",
        "paid_up_capital": 280, "compliance_profile": "moderate",
    },
    # ---- CREDIT REFERENCE BUREAUS ----
    {
        "institution_code": "CRB-601", "institution_name": "Credit Reference Bureau Africa Limited",
        "tier": "credit_reference", "license_number": "BOU/CRB/001", "region": "Kampala",
        "registered_address": "Plot 37/39, Nakasero Road, Kampala",
        "paid_up_capital": 520, "compliance_profile": "strong",
    },
    {
        "institution_code": "CRB-602", "institution_name": "Metropol CRB Uganda Limited",
        "tier": "credit_reference", "license_number": "BOU/CRB/002", "region": "Kampala",
        "registered_address": "Garden City Mall, Yusuf Lule Road, Kampala",
        "paid_up_capital": 505, "compliance_profile": "moderate",
    },
]


def generate_compliance_metrics(institution: Dict, seed_offset: int = 0) -> Dict:
    """
    Generate realistic compliance metrics for an institution based on its profile.
    compliance_profile: 'strong' | 'moderate' | 'at_risk'
    """
    rng = random.Random(seed_offset + hash(institution["institution_code"]))
    profile = institution.get("compliance_profile", "moderate")
    tier = institution["tier"]
    thresholds = BOU_THRESHOLDS.get(tier, BOU_THRESHOLDS["tier_1"])

    min_cap = thresholds["min_capital_ugx_millions"]
    paid_cap = institution.get("paid_up_capital", min_cap)

    if profile == "strong":
        core_car = rng.uniform(12.0, 18.0)
        total_car = rng.uniform(14.0, 22.0)
        liquidity = rng.uniform(25.0, 45.0)
        aml_score = rng.uniform(82.0, 97.0)
        governance_score = rng.uniform(85.0, 98.0)
        outstanding_reports = 0
        qtr_current = True
        annual_current = True
        board_compliant = True
        str_submitted = True
        aml_audit = True
        dpf_current = True
        fraud_rate = rng.uniform(0.1, 1.5)
    elif profile == "moderate":
        core_car = rng.uniform(8.5, 12.5)
        total_car = rng.uniform(12.5, 15.0)
        liquidity = rng.uniform(20.0, 28.0)
        aml_score = rng.uniform(65.0, 82.0)
        governance_score = rng.uniform(70.0, 85.0)
        outstanding_reports = rng.randint(0, 2)
        qtr_current = rng.random() > 0.15
        annual_current = rng.random() > 0.1
        board_compliant = rng.random() > 0.2
        str_submitted = rng.random() > 0.2
        aml_audit = rng.random() > 0.15
        dpf_current = rng.random() > 0.1
        fraud_rate = rng.uniform(1.5, 4.0)
    else:  # at_risk
        core_car = rng.uniform(5.0, 8.5)
        total_car = rng.uniform(9.0, 12.5)
        liquidity = rng.uniform(10.0, 20.0)
        aml_score = rng.uniform(30.0, 65.0)
        governance_score = rng.uniform(40.0, 70.0)
        outstanding_reports = rng.randint(1, 5)
        qtr_current = rng.random() > 0.4
        annual_current = rng.random() > 0.35
        board_compliant = rng.random() > 0.45
        str_submitted = rng.random() > 0.45
        aml_audit = rng.random() > 0.4
        dpf_current = rng.random() > 0.35
        fraud_rate = rng.uniform(4.0, 12.0)

    # Calculate risk score (0-100, higher = worse)
    risk_flags = []
    risk_score = 0.0

    # Capital adequacy check
    min_threshold = thresholds["core_capital_ratio_min"]
    if min_threshold > 0 and core_car < min_threshold:
        risk_score += 30
        risk_flags.append(f"Core CAR {core_car:.1f}% below minimum {min_threshold}%")
    elif min_threshold > 0 and core_car < min_threshold + 1:
        risk_score += 15
        risk_flags.append(f"Core CAR {core_car:.1f}% near minimum threshold")

    # Capital adequacy for minimum paid-up capital
    if paid_cap < min_cap * 0.99:
        risk_score += 25
        risk_flags.append(f"Paid-up capital UGX {paid_cap:,.0f}M below required {min_cap:,.0f}M")

    # Liquidity check
    liq_min = thresholds["liquidity_ratio_min"]
    if liq_min > 0 and liquidity < liq_min:
        risk_score += 20
        risk_flags.append(f"Liquidity ratio {liquidity:.1f}% below minimum {liq_min}%")

    # AML/CFT compliance
    if aml_score < 50:
        risk_score += 20
        risk_flags.append("AML/CFT compliance score critically low")
    elif aml_score < 65:
        risk_score += 10
        risk_flags.append("AML/CFT compliance score below acceptable threshold")

    if not str_submitted:
        risk_score += 10
        risk_flags.append("Suspicious Transaction Reports not submitted (last quarter)")

    if not aml_audit:
        risk_score += 8
        risk_flags.append("AML audit report overdue")

    # Reporting
    if outstanding_reports > 0:
        risk_score += outstanding_reports * 5
        risk_flags.append(f"{outstanding_reports} outstanding regulatory report(s)")

    if not qtr_current:
        risk_score += 10
        risk_flags.append("Quarterly returns not current")

    if not annual_current:
        risk_score += 8
        risk_flags.append("Annual returns not submitted")

    # Corporate governance
    if not board_compliant:
        risk_score += 12
        risk_flags.append("Board composition non-compliant (< 4 independent non-exec directors)")

    # DPF contribution
    if not dpf_current:
        risk_score += 8
        risk_flags.append("Deposit Protection Fund contribution overdue")

    # Fraud rate
    if fraud_rate > 5.0:
        risk_score += 15
        risk_flags.append(f"High transaction fraud rate: {fraud_rate:.1f}%")
    elif fraud_rate > 3.0:
        risk_score += 7
        risk_flags.append(f"Elevated fraud rate: {fraud_rate:.1f}%")

    risk_score = min(100.0, risk_score)

    # Compliance score (inverse of risk, but also accounts for positives)
    compliance_score = max(0.0, 100.0 - risk_score * 0.9)

    # Compliance status
    if risk_score >= 60:
        compliance_status = "non_compliant"
    elif risk_score >= 35:
        compliance_status = "warning"
    elif risk_score >= 15:
        compliance_status = "under_review"
    else:
        compliance_status = "compliant"

    # Dates
    now = datetime.now(timezone.utc)
    months_since_inspection = rng.randint(1, 14)
    last_inspection = now - timedelta(days=30 * months_since_inspection)
    next_inspection = last_inspection + timedelta(days=365)

    license_issue = now - timedelta(days=rng.randint(365 * 2, 365 * 15))
    license_expiry = license_issue + timedelta(days=365 * 3)

    txns_30d = rng.randint(500, 50000)
    flagged_30d = int(txns_30d * fraud_rate / 100)

    return {
        "license_issue_date": license_issue,
        "license_expiry_date": license_expiry,
        "paid_up_capital": paid_cap,
        "capital_adequacy_ratio": round(total_car, 2),
        "core_capital_ratio": round(core_car, 2),
        "total_capital_ratio": round(total_car, 2),
        "liquidity_ratio": round(liquidity, 2),
        "aml_policy_submitted": True,
        "cdd_procedures_compliant": aml_score > 60,
        "str_submitted_last_quarter": str_submitted,
        "aml_audit_report_current": aml_audit,
        "fatf_compliance_score": round(aml_score, 1),
        "quarterly_returns_current": qtr_current,
        "annual_returns_submitted": annual_current,
        "last_inspection_date": last_inspection,
        "next_inspection_due": next_inspection,
        "outstanding_reports": outstanding_reports,
        "board_compliant": board_compliant,
        "ceo_approved": rng.random() > 0.05,
        "company_secretary_approved": rng.random() > 0.05,
        "governance_score": round(governance_score, 1),
        "overall_risk_score": round(risk_score, 1),
        "compliance_score": round(compliance_score, 1),
        "compliance_status": compliance_status,
        "risk_flags": json.dumps(risk_flags),
        "dpf_contribution_current": dpf_current,
        "total_transactions_30d": txns_30d,
        "flagged_transactions_30d": flagged_30d,
        "fraud_rate_30d": round(fraud_rate, 2),
        "high_risk_transaction_volume": round(rng.uniform(1e8, 5e10), 0),
        "minimum_capital_required": BOU_THRESHOLDS.get(institution["tier"], {}).get("min_capital_ugx_millions", 0),
    }


def get_sector_summary(institutions: List[Dict]) -> Dict:
    """Aggregate summary statistics for the BOU institution monitoring dashboard."""
    total = len(institutions)
    if total == 0:
        return {}

    compliant = sum(1 for i in institutions if i["compliance_status"] == "compliant")
    warning = sum(1 for i in institutions if i["compliance_status"] == "warning")
    under_review = sum(1 for i in institutions if i["compliance_status"] == "under_review")
    non_compliant = sum(1 for i in institutions if i["compliance_status"] == "non_compliant")
    suspended = sum(1 for i in institutions if i["compliance_status"] == "suspended")

    tier_breakdown = {}
    for inst in institutions:
        t = inst["tier"]
        if t not in tier_breakdown:
            tier_breakdown[t] = {"total": 0, "compliant": 0, "at_risk": 0}
        tier_breakdown[t]["total"] += 1
        if inst["compliance_status"] == "compliant":
            tier_breakdown[t]["compliant"] += 1
        elif inst["compliance_status"] in ("non_compliant", "warning"):
            tier_breakdown[t]["at_risk"] += 1

    avg_risk = sum(i["overall_risk_score"] for i in institutions) / total
    avg_compliance = sum(i["compliance_score"] for i in institutions) / total
    total_txns = sum(i.get("total_transactions_30d", 0) for i in institutions)
    total_flagged = sum(i.get("flagged_transactions_30d", 0) for i in institutions)

    return {
        "total_institutions": total,
        "compliant_count": compliant,
        "warning_count": warning,
        "under_review_count": under_review,
        "non_compliant_count": non_compliant,
        "suspended_count": suspended,
        "compliance_rate_pct": round(compliant / total * 100, 1),
        "non_compliance_rate_pct": round((non_compliant + suspended) / total * 100, 1),
        "average_risk_score": round(avg_risk, 1),
        "average_compliance_score": round(avg_compliance, 1),
        "tier_breakdown": tier_breakdown,
        "sector_transactions_30d": total_txns,
        "sector_flagged_30d": total_flagged,
        "sector_fraud_rate_pct": round(total_flagged / total_txns * 100, 2) if total_txns else 0,
    }