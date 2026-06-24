"""
BOU Sentinel - Institution Seed Data
All institutions currently supervised by the Bank of Uganda.

Sources:
  - BOU Supervised Institutions (October 2025): bou.or.ug/bouwebsite/Supervision/
  - Wikipedia List of banks in Uganda (updated Oct 2025)
  - FI (Revision of Min Capital Requirements) Instrument 2022
  - BOU Integrated Annual Report 2024/2025

Account prefix map: first 3 characters of sender_account → institution_code.
Mock transaction generators should use these prefixes so Sentinel can link
transactions to institutions in real-time.
"""
import json
import logging
import random
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("bou-sentinel.seed")

# ─────────────────────────────────────────────────────────────────────────────
# ACCOUNT PREFIX → INSTITUTION CODE MAPPING
# Used by create_transaction() to link transactions to supervised institutions.
# ─────────────────────────────────────────────────────────────────────────────
ACCOUNT_PREFIX_MAP: dict[str, str] = {
    # Tier I — Commercial Banks
    "STB": "STANBIC_UG",
    "CEN": "CENTENARY_UG",
    "DFC": "DFCU_UG",
    "ABS": "ABSA_UG",
    "SCB": "STANCHART_UG",
    "CTB": "CITI_UG",
    "EQB": "EQUITY_UG",
    "DTB": "DTB_UG",
    "ECO": "ECOBANK_UG",
    "KCB": "KCB_UG",
    "BOA": "BOA_UG",
    "BRB": "BARODA_UG",
    "BOI": "BANKINDIA_UG",
    "CAI": "CAIRO_UG",
    "EXI": "EXIM_UG",
    "HFB": "HFB_UG",
    "NCB": "NCBA_UG",
    "IMB": "IM_UG",
    "SLM": "SALAAM_UG",
    "TRO": "TROPICAL_UG",
    "UBA": "UBA_UG",
    "PLB": "PEARL_UG",
    # Tier II — Credit Institutions
    "ABC": "ABC_UG",
    "GTB": "GTB_UG",
    "OPP": "OPPORTUNITY_UG",
    "YKB": "YAKO_UG",
    "BRC": "BRAC_UG",
    "FTB": "FINAN_TRUST_UG",
    "PRB": "PRIDE_BANK_UG",
    # Tier III — MDIs
    "FIN": "FINCA_UG",
    "PRM": "PRIDE_MDI_UG",
    "UGA": "UGAFODE_UG",
    # Non-Bank Payment Service Providers
    "MTN": "MTN_MOMO_UG",
    "ATL": "AIRTEL_MONEY_UG",
}


def get_institution_from_account(account: str) -> str | None:
    """
    Infer institution_code from the first 3 characters of an account number.
    Returns None if the prefix is not recognised.
    """
    if not account or len(account) < 3:
        return None
    return ACCOUNT_PREFIX_MAP.get(account[:3].upper())


# ─────────────────────────────────────────────────────────────────────────────
# INSTITUTION SEED DATA
# Metrics are representative / illustrative — not official BOU disclosures.
# Risk spread is intentional for demo purposes:
#   CRITICAL  : Yako Bank  (AML non-compliant + low liquidity + governance gaps)
#   HIGH      : Cairo Bank (under_review + liquidity breach + governance gaps)
#   MEDIUM    : GTB Uganda, Bank of India, Tropical Bank
#   LOW       : All fully-compliant Tier I banks
# ─────────────────────────────────────────────────────────────────────────────
_INSTITUTIONS: list[dict] = [

    # ═══════════════════════════════════════════════════════════════════════
    # TIER I — COMMERCIAL BANKS  (min paid-up capital: UGX 150 billion)
    # ═══════════════════════════════════════════════════════════════════════
    {
        "institution_code": "STANBIC_UG",
        "name": "Stanbic Bank Uganda Limited",
        "tier": "Tier I",
        "institution_type": "Commercial Bank",
        "license_status": "active",
        "licensed_since": "1991",
        "paid_up_capital_ugx_bn": 312.5,
        "minimum_capital_required_ugx_bn": 150.0,
        "core_capital_ratio": 21.3,
        "total_capital_ratio": 24.8,
        "liquidity_ratio": 38.4,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 28,
        "independent_directors_count": 6,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "CENTENARY_UG",
        "name": "Centenary Rural Development Bank Limited",
        "tier": "Tier I",
        "institution_type": "Commercial Bank",
        "license_status": "active",
        "licensed_since": "1993",
        "paid_up_capital_ugx_bn": 187.3,
        "minimum_capital_required_ugx_bn": 150.0,
        "core_capital_ratio": 17.9,
        "total_capital_ratio": 21.2,
        "liquidity_ratio": 31.6,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 45,
        "independent_directors_count": 5,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "DFCU_UG",
        "name": "DFCU Bank Limited",
        "tier": "Tier I",
        "institution_type": "Commercial Bank",
        "license_status": "active",
        "licensed_since": "1964",
        "paid_up_capital_ugx_bn": 163.1,
        "minimum_capital_required_ugx_bn": 150.0,
        "core_capital_ratio": 16.4,
        "total_capital_ratio": 19.7,
        "liquidity_ratio": 28.3,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 32,
        "independent_directors_count": 5,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "ABSA_UG",
        "name": "Absa Bank Uganda Limited",
        "tier": "Tier I",
        "institution_type": "Commercial Bank",
        "license_status": "active",
        "licensed_since": "1969",
        "paid_up_capital_ugx_bn": 289.4,
        "minimum_capital_required_ugx_bn": 150.0,
        "core_capital_ratio": 19.8,
        "total_capital_ratio": 22.6,
        "liquidity_ratio": 35.1,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 21,
        "independent_directors_count": 6,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "STANCHART_UG",
        "name": "Standard Chartered Bank Uganda Limited",
        "tier": "Tier I",
        "institution_type": "Commercial Bank",
        "license_status": "active",
        "licensed_since": "1912",
        "paid_up_capital_ugx_bn": 245.7,
        "minimum_capital_required_ugx_bn": 150.0,
        "core_capital_ratio": 18.6,
        "total_capital_ratio": 21.9,
        "liquidity_ratio": 42.7,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 15,
        "independent_directors_count": 5,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "CITI_UG",
        "name": "Citibank Uganda Limited",
        "tier": "Tier I",
        "institution_type": "Commercial Bank",
        "license_status": "active",
        "licensed_since": "1999",
        "paid_up_capital_ugx_bn": 178.2,
        "minimum_capital_required_ugx_bn": 150.0,
        "core_capital_ratio": 15.3,
        "total_capital_ratio": 18.1,
        "liquidity_ratio": 29.8,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 38,
        "independent_directors_count": 5,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "EQUITY_UG",
        "name": "Equity Bank Uganda Limited",
        "tier": "Tier I",
        "institution_type": "Commercial Bank",
        "license_status": "active",
        "licensed_since": "2008",
        "paid_up_capital_ugx_bn": 152.6,
        "minimum_capital_required_ugx_bn": 150.0,
        "core_capital_ratio": 12.1,
        "total_capital_ratio": 14.8,
        "liquidity_ratio": 23.4,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 55,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "DTB_UG",
        "name": "Diamond Trust Bank Uganda Limited",
        "tier": "Tier I",
        "institution_type": "Commercial Bank",
        "license_status": "active",
        "licensed_since": "1996",
        "paid_up_capital_ugx_bn": 159.3,
        "minimum_capital_required_ugx_bn": 150.0,
        "core_capital_ratio": 13.7,
        "total_capital_ratio": 16.2,
        "liquidity_ratio": 25.6,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 42,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "ECOBANK_UG",
        "name": "Ecobank Uganda Limited",
        "tier": "Tier I",
        "institution_type": "Commercial Bank",
        "license_status": "active",
        "licensed_since": "1994",
        "paid_up_capital_ugx_bn": 155.8,
        "minimum_capital_required_ugx_bn": 150.0,
        "core_capital_ratio": 11.4,
        "total_capital_ratio": 13.9,
        "liquidity_ratio": 21.7,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 60,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "KCB_UG",
        "name": "KCB Bank Uganda Limited",
        "tier": "Tier I",
        "institution_type": "Commercial Bank",
        "license_status": "active",
        "licensed_since": "2007",
        "paid_up_capital_ugx_bn": 161.4,
        "minimum_capital_required_ugx_bn": 150.0,
        "core_capital_ratio": 14.2,
        "total_capital_ratio": 17.1,
        "liquidity_ratio": 26.9,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 50,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "BOA_UG",
        "name": "Bank of Africa Uganda Limited",
        "tier": "Tier I",
        "institution_type": "Commercial Bank",
        "license_status": "active",
        "licensed_since": "1985",
        "paid_up_capital_ugx_bn": 153.9,
        "minimum_capital_required_ugx_bn": 150.0,
        "core_capital_ratio": 10.8,
        "total_capital_ratio": 13.4,
        "liquidity_ratio": 20.6,   # just above 20% — mild notice
        "aml_compliance_status": "compliant",
        "aml_days_ago": 74,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "BARODA_UG",
        "name": "Bank of Baroda Uganda Limited",
        "tier": "Tier I",
        "institution_type": "Commercial Bank",
        "license_status": "active",
        "licensed_since": "1953",
        "paid_up_capital_ugx_bn": 167.2,
        "minimum_capital_required_ugx_bn": 150.0,
        "core_capital_ratio": 14.6,
        "total_capital_ratio": 17.8,
        "liquidity_ratio": 27.3,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 30,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "BANKINDIA_UG",
        "name": "Bank of India (Uganda) Limited",
        "tier": "Tier I",
        "institution_type": "Commercial Bank",
        "license_status": "active",
        "licensed_since": "1953",
        "paid_up_capital_ugx_bn": 151.8,
        "minimum_capital_required_ugx_bn": 150.0,
        "core_capital_ratio": 9.7,
        "total_capital_ratio": 12.3,
        "liquidity_ratio": 20.2,   # barely above minimum — MEDIUM risk
        "aml_compliance_status": "compliant",
        "aml_days_ago": 80,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        # ── DEMO: HIGH-RISK institution ──────────────────────────────────────
        # License under_review + liquidity breach + AML pending + governance gaps
        "institution_code": "CAIRO_UG",
        "name": "Cairo Bank Uganda Limited",
        "tier": "Tier I",
        "institution_type": "Commercial Bank",
        "license_status": "under_review",
        "licensed_since": "1995",
        "paid_up_capital_ugx_bn": 150.5,
        "minimum_capital_required_ugx_bn": 150.0,
        "core_capital_ratio": 8.2,
        "total_capital_ratio": 12.1,
        "liquidity_ratio": 17.8,          # BELOW 20% minimum
        "aml_compliance_status": "pending",
        "aml_days_ago": 148,              # overdue
        "independent_directors_count": 3, # BELOW minimum of 4
        "has_internal_auditor": True,
        "has_company_secretary": False,   # missing
        "headquarters": "Kampala",
    },
    {
        "institution_code": "EXIM_UG",
        "name": "Exim Bank Uganda Limited",
        "tier": "Tier I",
        "institution_type": "Commercial Bank",
        "license_status": "active",
        "licensed_since": "2011",
        "paid_up_capital_ugx_bn": 156.4,
        "minimum_capital_required_ugx_bn": 150.0,
        "core_capital_ratio": 11.9,
        "total_capital_ratio": 14.7,
        "liquidity_ratio": 23.1,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 33,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "HFB_UG",
        "name": "Housing Finance Bank Uganda Limited",
        "tier": "Tier I",
        "institution_type": "Commercial Bank",
        "license_status": "active",
        "licensed_since": "1967",
        "paid_up_capital_ugx_bn": 158.7,
        "minimum_capital_required_ugx_bn": 150.0,
        "core_capital_ratio": 12.4,
        "total_capital_ratio": 15.3,
        "liquidity_ratio": 24.8,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 25,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "NCBA_UG",
        "name": "NCBA Bank Uganda Limited",
        "tier": "Tier I",
        "institution_type": "Commercial Bank",
        "license_status": "active",
        "licensed_since": "2010",
        "paid_up_capital_ugx_bn": 154.3,
        "minimum_capital_required_ugx_bn": 150.0,
        "core_capital_ratio": 10.6,
        "total_capital_ratio": 13.2,
        "liquidity_ratio": 22.5,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 47,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "IM_UG",
        "name": "I&M Bank (Uganda) Limited",
        "tier": "Tier I",
        "institution_type": "Commercial Bank",
        "license_status": "active",
        "licensed_since": "2013",
        "paid_up_capital_ugx_bn": 157.9,
        "minimum_capital_required_ugx_bn": 150.0,
        "core_capital_ratio": 13.1,
        "total_capital_ratio": 15.8,
        "liquidity_ratio": 25.2,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 40,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "SALAAM_UG",
        "name": "Salaam Bank Uganda",
        "tier": "Tier I",
        "institution_type": "Commercial Bank (Islamic)",
        "license_status": "active",
        "licensed_since": "2023",          # First Islamic banking licence — BOU Sept 2023
        "paid_up_capital_ugx_bn": 152.1,
        "minimum_capital_required_ugx_bn": 150.0,
        "core_capital_ratio": 9.8,
        "total_capital_ratio": 12.6,
        "liquidity_ratio": 24.1,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 35,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "TROPICAL_UG",
        "name": "Tropical Bank Limited",
        "tier": "Tier I",
        "institution_type": "Commercial Bank",
        "license_status": "active",
        "licensed_since": "1973",
        "paid_up_capital_ugx_bn": 153.4,
        "minimum_capital_required_ugx_bn": 150.0,
        "core_capital_ratio": 10.2,
        "total_capital_ratio": 12.8,
        "liquidity_ratio": 21.1,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 78,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "UBA_UG",
        "name": "United Bank for Africa Uganda Limited",
        "tier": "Tier I",
        "institution_type": "Commercial Bank",
        "license_status": "active",
        "licensed_since": "2008",
        "paid_up_capital_ugx_bn": 155.6,
        "minimum_capital_required_ugx_bn": 150.0,
        "core_capital_ratio": 11.7,
        "total_capital_ratio": 14.3,
        "liquidity_ratio": 22.9,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 52,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "PEARL_UG",
        "name": "Pearl Bank Uganda Limited",
        "tier": "Tier I",
        "institution_type": "Commercial Bank",
        "license_status": "active",
        "licensed_since": "2023",
        "paid_up_capital_ugx_bn": 150.3,
        "minimum_capital_required_ugx_bn": 150.0,
        "core_capital_ratio": 8.4,
        "total_capital_ratio": 12.2,
        "liquidity_ratio": 20.8,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 44,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # TIER II — CREDIT INSTITUTIONS  (min paid-up capital: UGX 25 billion)
    # (3 banks downgraded from Tier I: Guaranty Trust, ABC Capital, Opportunity — March 2024)
    # ═══════════════════════════════════════════════════════════════════════
    {
        "institution_code": "ABC_UG",
        "name": "ABC Capital Bank Uganda Limited",
        "tier": "Tier II",
        "institution_type": "Credit Institution",
        "license_status": "active",
        "licensed_since": "1999",
        "paid_up_capital_ugx_bn": 27.4,
        "minimum_capital_required_ugx_bn": 25.0,
        "core_capital_ratio": 12.6,
        "total_capital_ratio": 15.4,
        "liquidity_ratio": 23.8,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 36,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "GTB_UG",
        "name": "Guaranty Trust Bank (Uganda) Limited",
        "tier": "Tier II",
        "institution_type": "Credit Institution",
        "license_status": "active",
        "licensed_since": "2008",
        "paid_up_capital_ugx_bn": 25.8,
        "minimum_capital_required_ugx_bn": 25.0,
        "core_capital_ratio": 10.3,
        "total_capital_ratio": 13.1,
        "liquidity_ratio": 16.4,           # BELOW 20% minimum — MEDIUM risk
        "aml_compliance_status": "pending",
        "aml_days_ago": 105,               # overdue
        "independent_directors_count": 3,  # BELOW minimum
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "OPPORTUNITY_UG",
        "name": "Opportunity Bank Uganda Limited",
        "tier": "Tier II",
        "institution_type": "Credit Institution",
        "license_status": "active",
        "licensed_since": "2004",
        "paid_up_capital_ugx_bn": 26.3,
        "minimum_capital_required_ugx_bn": 25.0,
        "core_capital_ratio": 11.2,
        "total_capital_ratio": 13.8,
        "liquidity_ratio": 21.5,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 58,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        # ── DEMO: CRITICAL-RISK institution ─────────────────────────────────
        # AML non-compliant + liquidity breach + no auditor + governance gaps
        "institution_code": "YAKO_UG",
        "name": "Yako Bank Uganda Limited",
        "tier": "Tier II",
        "institution_type": "Credit Institution",
        "license_status": "active",
        "licensed_since": "2016",
        "paid_up_capital_ugx_bn": 25.2,
        "minimum_capital_required_ugx_bn": 25.0,
        "core_capital_ratio": 9.4,
        "total_capital_ratio": 12.2,
        "liquidity_ratio": 14.7,           # BELOW 20% — critical
        "aml_compliance_status": "non_compliant",  # FIA flagged
        "aml_days_ago": 185,               # extremely overdue
        "independent_directors_count": 3,  # BELOW minimum
        "has_internal_auditor": False,     # MISSING
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "BRAC_UG",
        "name": "BRAC Uganda Bank Limited",
        "tier": "Tier II",
        "institution_type": "Credit Institution",
        "license_status": "active",
        "licensed_since": "2019",
        "paid_up_capital_ugx_bn": 26.1,
        "minimum_capital_required_ugx_bn": 25.0,
        "core_capital_ratio": 10.8,
        "total_capital_ratio": 13.6,
        "liquidity_ratio": 22.1,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 29,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "FINAN_TRUST_UG",
        "name": "Finance Trust Bank",
        "tier": "Tier II",
        "institution_type": "Credit Institution",
        "license_status": "active",
        "licensed_since": "2013",
        "paid_up_capital_ugx_bn": 25.5,
        "minimum_capital_required_ugx_bn": 25.0,
        "core_capital_ratio": 9.9,
        "total_capital_ratio": 12.4,
        "liquidity_ratio": 20.3,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 43,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "PRIDE_BANK_UG",
        "name": "Pride Bank Limited",
        "tier": "Tier II",
        "institution_type": "Credit Institution",
        "license_status": "active",
        "licensed_since": "2023",
        "paid_up_capital_ugx_bn": 25.1,
        "minimum_capital_required_ugx_bn": 25.0,
        "core_capital_ratio": 8.9,
        "total_capital_ratio": 12.1,
        "liquidity_ratio": 20.6,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 67,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # TIER III — MICROFINANCE DEPOSIT-TAKING INSTITUTIONS (MDIs)
    # (min paid-up capital: UGX 20 billion — as at January 2024: 3 licensed)
    # ═══════════════════════════════════════════════════════════════════════
    {
        "institution_code": "FINCA_UG",
        "name": "FINCA Uganda Limited (MDI)",
        "tier": "Tier III",
        "institution_type": "Microfinance Deposit-Taking Institution",
        "license_status": "active",
        "licensed_since": "2004",
        "paid_up_capital_ugx_bn": 22.4,
        "minimum_capital_required_ugx_bn": 20.0,
        "core_capital_ratio": 14.7,
        "total_capital_ratio": 17.3,
        "liquidity_ratio": 26.8,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 31,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "PRIDE_MDI_UG",
        "name": "PRIDE Microfinance Limited (MDI)",
        "tier": "Tier III",
        "institution_type": "Microfinance Deposit-Taking Institution",
        "license_status": "active",
        "licensed_since": "2005",
        "paid_up_capital_ugx_bn": 20.8,
        "minimum_capital_required_ugx_bn": 20.0,
        "core_capital_ratio": 11.3,
        "total_capital_ratio": 14.1,
        "liquidity_ratio": 23.4,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 49,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "UGAFODE_UG",
        "name": "UGAFODE Microfinance Limited (MDI)",
        "tier": "Tier III",
        "institution_type": "Microfinance Deposit-Taking Institution",
        "license_status": "active",
        "licensed_since": "2011",
        "paid_up_capital_ugx_bn": 20.3,
        "minimum_capital_required_ugx_bn": 20.0,
        "core_capital_ratio": 10.1,
        "total_capital_ratio": 12.9,
        "liquidity_ratio": 22.6,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 62,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # NON-BANK PAYMENT SERVICE PROVIDERS
    # (Supervised by BOU under National Payment Systems Act)
    # ═══════════════════════════════════════════════════════════════════════
    {
        "institution_code": "MTN_MOMO_UG",
        "name": "MTN Mobile Money Uganda Limited",
        "tier": "Non-Bank",
        "institution_type": "Non-Bank Payment Service Provider",
        "license_status": "active",
        "licensed_since": "2009",
        "paid_up_capital_ugx_bn": None,
        "minimum_capital_required_ugx_bn": None,
        "core_capital_ratio": None,
        "total_capital_ratio": None,
        "liquidity_ratio": None,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 20,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
    {
        "institution_code": "AIRTEL_MONEY_UG",
        "name": "Airtel Money Uganda Limited",
        "tier": "Non-Bank",
        "institution_type": "Non-Bank Payment Service Provider",
        "license_status": "active",
        "licensed_since": "2011",
        "paid_up_capital_ugx_bn": None,
        "minimum_capital_required_ugx_bn": None,
        "core_capital_ratio": None,
        "total_capital_ratio": None,
        "liquidity_ratio": None,
        "aml_compliance_status": "compliant",
        "aml_days_ago": 27,
        "independent_directors_count": 4,
        "has_internal_auditor": True,
        "has_company_secretary": True,
        "headquarters": "Kampala",
    },
]


def seed_institutions(db_session) -> int:
    """
    Seed all BOU-supervised institutions into the database.
    Idempotent — skips institutions that already exist.
    Computes initial risk score for each institution via the compliance engine.

    Returns the number of newly seeded records.
    """
    from app.regulatory_models import Institution
    from app.compliance_engine import calculate_compliance_risk

    seeded = 0
    now = datetime.now(timezone.utc)

    for data in _INSTITUTIONS:
        exists = (
            db_session.query(Institution)
            .filter_by(institution_code=data["institution_code"])
            .first()
        )
        if exists:
            continue

        aml_date = now - timedelta(days=data.pop("aml_days_ago", 30))

        # Initial risk calculation
        risk_score, risk_level, issues = calculate_compliance_risk(
            {**data, "aml_last_report_date": aml_date},
            fraud_stats={"fraud_rate": 0.0},
        )

        inst = Institution(
            institution_code=data["institution_code"],
            name=data["name"],
            tier=data["tier"],
            institution_type=data["institution_type"],
            license_status=data.get("license_status", "active"),
            licensed_since=data.get("licensed_since"),
            paid_up_capital_ugx_bn=data.get("paid_up_capital_ugx_bn"),
            minimum_capital_required_ugx_bn=data.get("minimum_capital_required_ugx_bn"),
            core_capital_ratio=data.get("core_capital_ratio"),
            total_capital_ratio=data.get("total_capital_ratio"),
            liquidity_ratio=data.get("liquidity_ratio"),
            aml_last_report_date=aml_date,
            aml_compliance_status=data.get("aml_compliance_status", "compliant"),
            independent_directors_count=data.get("independent_directors_count", 4),
            has_internal_auditor=data.get("has_internal_auditor", True),
            has_company_secretary=data.get("has_company_secretary", True),
            risk_score=risk_score,
            risk_level=risk_level,
            compliance_issues=json.dumps(issues),
            headquarters=data.get("headquarters", "Kampala"),
        )
        db_session.add(inst)
        seeded += 1

    db_session.commit()
    logger.info(f"✅ Institutions seeded: {seeded} new records inserted")
    return seeded