"""
BOU Sentinel — Institution Seed Data
All institutions currently supervised by the Bank of Uganda (June 2026).

BOU-supervised categories (bou.or.ug/supervision):
  Tier I   — Commercial Banks (22)             Financial Institutions Act 2004 (Amended 2023)
  Tier II  — Credit Institutions (7)           Financial Institutions Act 2004
  Tier III — MDIs incl. EBO SACCO (4)         MDI Act 2003 + MDI Registered Societies Regs 2023
  Non-Bank — Forex Bureaux (200+)              Foreign Exchange Act 2004 + FX Regs 2006
  Non-Bank — Money Remitters (16)              Foreign Exchange Act 2004 + FX Regs 2006
  Non-Bank — Non-Bank PSPs (8)                 National Payment Systems Act 2020
  Non-Bank — Credit Reference Bureaus (2)      FI (CRB) Regulations 2022
  Non-Bank — Large SACCOs (BOU supervised)     MDI (Registered Societies) Regs 2023

NOT supervised by BOU: Tier IV MFIs, regular SACCOs, insurance (IRA),
capital markets (CMA), pensions (URBRA), money lenders (UMRA/MoFPED).

Sources:
  bou.or.ug/supervision  |  senteguide.com/providers/forex-bureaus
  Wikipedia List of banks in Uganda (Oct 2025)
  BOU Press Releases 2024–2026 | IMF/FATF Uganda Reports
"""
import json
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("bou-sentinel.seed")

# ─────────────────────────────────────────────────────────────────────────────
# ACCOUNT PREFIX → INSTITUTION CODE
# First 3 chars of sender_account → institution_code.
# Mock transaction generators use these so Sentinel can link transactions
# to institutions in real-time.
# ─────────────────────────────────────────────────────────────────────────────
ACCOUNT_PREFIX_MAP: dict[str, str] = {
    # Tier I — Commercial Banks
    "STB": "STANBIC_UG",       "CEN": "CENTENARY_UG",
    "DFC": "DFCU_UG",          "ABS": "ABSA_UG",
    "SCB": "STANCHART_UG",     "CTB": "CITI_UG",
    "EQB": "EQUITY_UG",        "DTB": "DTB_UG",
    "ECO": "ECOBANK_UG",       "KCB": "KCB_UG",
    "BOA": "BOA_UG",           "BRB": "BARODA_UG",
    "BOI": "BANKINDIA_UG",     "CAI": "CAIRO_UG",
    "EXI": "EXIM_UG",          "HFB": "HFB_UG",
    "NCB": "NCBA_UG",          "IMB": "IM_UG",
    "SLM": "SALAAM_UG",        "TRO": "TROPICAL_UG",
    "UBA": "UBA_UG",           "PLB": "PEARL_UG",
    # Tier II — Credit Institutions
    "ABC": "ABC_UG",            "GTB": "GTB_UG",
    "OPP": "OPPORTUNITY_UG",   "YKB": "YAKO_UG",
    "BRC": "BRAC_UG",          "FTB": "FINAN_TRUST_UG",
    "PRB": "PRIDE_BANK_UG",
    # Tier III — MDIs
    "FIN": "FINCA_UG",         "PRM": "PRIDE_MDI_UG",
    "UGA": "UGAFODE_UG",       "EBO": "EBO_SACCO",
    # Non-Bank PSPs
    "MTN": "MTN_MOMO_UG",      "ATL": "AIRTEL_MONEY_UG",
    "YOG": "YO_UGANDA",        "EZE": "EZEE_MONEY_UG",
    "PES": "PESAPAL_UG",
    # Major Forex Bureaux
    "MFB": "METROPOLITAN_FXB", "KWF": "KW_FXB",
    "DAH": "DAHABSHIIL_FXB",   "LDR": "LACEDRI_FXB",
    "GFB": "GUILD_FRANK_FXB",  "JTS": "JETSET_FXB",
    "NRF": "NORFRAX_FXB",      "KMW": "KAMWE_FXB",
    "ASN": "ASIAN_OVERSEAS",   "BKL": "BAKAAL_FXB",
    "CAP": "CAPITAL_FXB",      "DLH": "DOLLAR_HOUSE_FXB",
    "JBX": "JUBA_EXPRESS_FXB", "ASL": "ASAL_EXPRESS",
    # Credit Reference Bureaus
    "MTP": "METROPOL_CRB",     "TRU": "TRANSUNION_CRB",
    # Money Remitters
    "MKR": "MUKURU_UG",        "RIA": "RIA_MONEY_UG",
}


def get_institution_from_account(account: str) -> str | None:
    """Return institution_code from first 3 chars of account number, or None."""
    if not account or len(account) < 3:
        return None
    return ACCOUNT_PREFIX_MAP.get(account[:3].upper())


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _bank(code, name, tier, inst_type, since, capital, min_cap,
          core, total, liq, aml_status, aml_days,
          directors=4, auditor=True, secretary=True,
          hq="Kampala", license_status="active"):
    return dict(
        institution_code=code, name=name, tier=tier,
        institution_type=inst_type, license_status=license_status,
        licensed_since=since, paid_up_capital_ugx_bn=capital,
        minimum_capital_required_ugx_bn=min_cap,
        core_capital_ratio=core, total_capital_ratio=total,
        liquidity_ratio=liq, aml_compliance_status=aml_status,
        aml_days_ago=aml_days, independent_directors_count=directors,
        has_internal_auditor=auditor, has_company_secretary=secretary,
        headquarters=hq,
    )


def _nonbank(code, name, inst_type, since, aml_status="compliant",
             aml_days=30, directors=2, auditor=True, secretary=True,
             hq="Kampala", license_status="active"):
    return dict(
        institution_code=code, name=name, tier="Non-Bank",
        institution_type=inst_type, license_status=license_status,
        licensed_since=since,
        paid_up_capital_ugx_bn=None, minimum_capital_required_ugx_bn=None,
        core_capital_ratio=None, total_capital_ratio=None, liquidity_ratio=None,
        aml_compliance_status=aml_status, aml_days_ago=aml_days,
        independent_directors_count=directors,
        has_internal_auditor=auditor, has_company_secretary=secretary,
        headquarters=hq,
    )


# ─────────────────────────────────────────────────────────────────────────────
# ALL BOU-SUPERVISED INSTITUTIONS
# ─────────────────────────────────────────────────────────────────────────────
_INSTITUTIONS: list[dict] = [

    # ═════════════════════════════════════════════════════════════════════════
    # TIER I — COMMERCIAL BANKS (22)
    # Min paid-up capital: UGX 150 billion (FI Min Capital Req. Instrument 2022)
    # Core CAR ≥ 8 % | Total CAR ≥ 12 % | Liquidity ≥ 20 %
    # ═════════════════════════════════════════════════════════════════════════
    _bank("STANBIC_UG",   "Stanbic Bank Uganda Limited",                 "Tier I","Commercial Bank",               "1991",312.5,150.0,21.3,24.8,38.4,"compliant",28,6),
    _bank("CENTENARY_UG", "Centenary Rural Development Bank Limited",    "Tier I","Commercial Bank",               "1993",187.3,150.0,17.9,21.2,31.6,"compliant",45,5),
    _bank("DFCU_UG",      "DFCU Bank Limited",                           "Tier I","Commercial Bank",               "1964",163.1,150.0,16.4,19.7,28.3,"compliant",32,5),
    _bank("ABSA_UG",      "Absa Bank Uganda Limited",                    "Tier I","Commercial Bank",               "1969",289.4,150.0,19.8,22.6,35.1,"compliant",21,6),
    _bank("STANCHART_UG", "Standard Chartered Bank Uganda Limited",      "Tier I","Commercial Bank",               "1912",245.7,150.0,18.6,21.9,42.7,"compliant",15,5),
    _bank("CITI_UG",      "Citibank Uganda Limited",                     "Tier I","Commercial Bank",               "1999",178.2,150.0,15.3,18.1,29.8,"compliant",38,5),
    _bank("EQUITY_UG",    "Equity Bank Uganda Limited",                  "Tier I","Commercial Bank",               "2008",152.6,150.0,12.1,14.8,23.4,"compliant",55,4),
    _bank("DTB_UG",       "Diamond Trust Bank Uganda Limited",           "Tier I","Commercial Bank",               "1996",159.3,150.0,13.7,16.2,25.6,"compliant",42,4),
    _bank("ECOBANK_UG",   "Ecobank Uganda Limited",                      "Tier I","Commercial Bank",               "1994",155.8,150.0,11.4,13.9,21.7,"compliant",60,4),
    _bank("KCB_UG",       "KCB Bank Uganda Limited",                     "Tier I","Commercial Bank",               "2007",161.4,150.0,14.2,17.1,26.9,"compliant",50,4),
    _bank("BOA_UG",       "Bank of Africa Uganda Limited",               "Tier I","Commercial Bank",               "1985",153.9,150.0,10.8,13.4,20.6,"compliant",74,4),
    _bank("BARODA_UG",    "Bank of Baroda Uganda Limited",               "Tier I","Commercial Bank",               "1953",167.2,150.0,14.6,17.8,27.3,"compliant",30,4),
    _bank("BANKINDIA_UG", "Bank of India (Uganda) Limited",              "Tier I","Commercial Bank",               "1953",151.8,150.0, 9.7,12.3,20.2,"compliant",80,4),
    # HIGH-RISK: license under_review + liquidity breach + AML pending + governance gaps
    _bank("CAIRO_UG",     "Cairo Bank Uganda Limited",                   "Tier I","Commercial Bank",               "1995",150.5,150.0, 8.2,12.1,17.8,"pending",148,3,True,False,"Kampala","under_review"),
    _bank("EXIM_UG",      "Exim Bank Uganda Limited",                    "Tier I","Commercial Bank",               "2011",156.4,150.0,11.9,14.7,23.1,"compliant",33,4),
    _bank("HFB_UG",       "Housing Finance Bank Uganda Limited",         "Tier I","Commercial Bank",               "1967",158.7,150.0,12.4,15.3,24.8,"compliant",25,4),
    _bank("NCBA_UG",      "NCBA Bank Uganda Limited",                    "Tier I","Commercial Bank",               "2010",154.3,150.0,10.6,13.2,22.5,"compliant",47,4),
    _bank("IM_UG",        "I&M Bank (Uganda) Limited",                   "Tier I","Commercial Bank",               "2013",157.9,150.0,13.1,15.8,25.2,"compliant",40,4),
    _bank("SALAAM_UG",    "Salaam Bank Uganda (Islamic Banking)",        "Tier I","Commercial Bank (Islamic)",      "2023",152.1,150.0, 9.8,12.6,24.1,"compliant",35,4),
    _bank("TROPICAL_UG",  "Tropical Bank Limited",                       "Tier I","Commercial Bank",               "1973",153.4,150.0,10.2,12.8,21.1,"compliant",78,4),
    _bank("UBA_UG",       "United Bank for Africa Uganda Limited",       "Tier I","Commercial Bank",               "2008",155.6,150.0,11.7,14.3,22.9,"compliant",52,4),
    _bank("PEARL_UG",     "Pearl Bank Uganda Limited",                   "Tier I","Commercial Bank",               "2023",150.3,150.0, 8.4,12.2,20.8,"compliant",44,4),

    # ═════════════════════════════════════════════════════════════════════════
    # TIER II — CREDIT INSTITUTIONS (7)
    # Min paid-up capital: UGX 25 billion
    # ABC, GTB, Opportunity downgraded from Tier I — March 2024
    # ═════════════════════════════════════════════════════════════════════════
    _bank("ABC_UG",         "ABC Capital Bank Uganda Limited",            "Tier II","Credit Institution",           "1999", 27.4,25.0,12.6,15.4,23.8,"compliant",36,4),
    _bank("GTB_UG",         "Guaranty Trust Bank (Uganda) Limited",       "Tier II","Credit Institution",           "2008", 25.8,25.0,10.3,13.1,16.4,"pending",105,3),  # MEDIUM: liq+AML+governance
    _bank("OPPORTUNITY_UG", "Opportunity Bank Uganda Limited",             "Tier II","Credit Institution",           "2004", 26.3,25.0,11.2,13.8,21.5,"compliant",58,4),
    # CRITICAL-RISK: AML non-compliant + liquidity breach + no auditor + governance
    _bank("YAKO_UG",        "Yako Bank Uganda Limited",                   "Tier II","Credit Institution",           "2016", 25.2,25.0, 9.4,12.2,14.7,"non_compliant",185,3,False,True),
    _bank("BRAC_UG",        "BRAC Uganda Bank Limited",                   "Tier II","Credit Institution",           "2019", 26.1,25.0,10.8,13.6,22.1,"compliant",29,4),
    _bank("FINAN_TRUST_UG", "Finance Trust Bank",                         "Tier II","Credit Institution",           "2013", 25.5,25.0, 9.9,12.4,20.3,"compliant",43,4),
    _bank("PRIDE_BANK_UG",  "Pride Bank Limited",                         "Tier II","Credit Institution",           "2023", 25.1,25.0, 8.9,12.1,20.6,"compliant",67,4),

    # ═════════════════════════════════════════════════════════════════════════
    # TIER III — MDIs (4; EFC Uganda revoked Jan 2024)
    # Min paid-up capital: UGX 20 billion | MDI Act 2003 (amended 2023)
    # EBO SACCO: first BOU-licensed SACCO under MDI Registered Societies Regs 2023 (Jan 28 2025)
    # ═════════════════════════════════════════════════════════════════════════
    _bank("FINCA_UG",    "FINCA Uganda Limited (MDI)",                    "Tier III","Microfinance Deposit-Taking Institution","2004",22.4,20.0,14.7,17.3,26.8,"compliant",31,4),
    _bank("PRIDE_MDI_UG","PRIDE Microfinance Limited (MDI)",              "Tier III","Microfinance Deposit-Taking Institution","2005",20.8,20.0,11.3,14.1,23.4,"compliant",49,4),
    _bank("UGAFODE_UG",  "UGAFODE Microfinance Limited (MDI)",            "Tier III","Microfinance Deposit-Taking Institution","2011",20.3,20.0,10.1,12.9,22.6,"compliant",62,4),
    # EBO SACCO — no capital ratios required under Registered Societies Regs
    _nonbank("EBO_SACCO","EBO Cooperative Savings & Credit Society Ltd",  "Large SACCO (BOU Supervised)","2025","compliant",15,4,True,True,"Mbarara"),

    # ═════════════════════════════════════════════════════════════════════════
    # NON-BANK PAYMENT SERVICE PROVIDERS (8)
    # National Payment Systems Act 2020
    # ═════════════════════════════════════════════════════════════════════════
    _nonbank("MTN_MOMO_UG",   "MTN Mobile Money Uganda Limited",          "Non-Bank Payment Service Provider","2009","compliant",20,4),
    _nonbank("AIRTEL_MONEY_UG","Airtel Money Uganda Limited",             "Non-Bank Payment Service Provider","2011","compliant",27,4),
    _nonbank("YO_UGANDA",     "Yo-Uganda Limited (Yo! Payments)",         "Non-Bank Payment Service Provider","2010","compliant",34,3),
    _nonbank("EZEE_MONEY_UG", "Ezee Money Uganda Limited",                "Non-Bank Payment Service Provider","2012","compliant",40,3),
    _nonbank("PESAPAL_UG",    "Pesapal Uganda Limited",                   "Non-Bank Payment Service Provider","2013","compliant",28,3),
    _nonbank("BEYONIC_UG",    "Beyonic Uganda Limited",                   "Non-Bank Payment Service Provider","2013","compliant",32,3),
    _nonbank("FLUTTERWAVE_UG","Flutterwave Technology Solutions Uganda",  "Non-Bank Payment Service Provider","2021","compliant",14,3),
    _nonbank("PAYWAY_UG",     "PayWay Uganda Limited",                    "Non-Bank Payment Service Provider","2011","compliant",45,3),

    # ═════════════════════════════════════════════════════════════════════════
    # MONEY REMITTERS (16)
    # Foreign Exchange Act 2004 + FX Regs 2006
    # Security deposit: UGX 50 million + AML compliance
    # ═════════════════════════════════════════════════════════════════════════
    _nonbank("DAHABSHIIL_UG",   "Dahabshiil Uganda Limited",             "Money Remitter","2004","compliant",20),
    _nonbank("MUKURU_UG",       "Mukuru Uganda Limited",                  "Money Remitter","2015","compliant",25),
    _nonbank("RIA_MONEY_UG",    "Ria Money Transfer Uganda Limited",      "Money Remitter","2012","compliant",30),
    _nonbank("ACE_MONEY_UG",    "ACE Money Transfer Uganda Limited",      "Money Remitter","2013","compliant",35),
    _nonbank("ASAL_EXPRESS",    "ASAL Express Money Transfer",            "Money Remitter","2010","compliant",28),
    _nonbank("REMITLY_UG",      "Remitly Uganda Limited",                 "Money Remitter","2019","compliant",18),
    _nonbank("XPRESS_MONEY",    "Xpress Money Services Uganda",           "Money Remitter","2011","compliant",33),
    _nonbank("TRANSFERWISE_UG", "Wise (formerly TransferWise) Uganda",    "Money Remitter","2020","compliant",15),
    _nonbank("WESTERN_UNION_UG","Western Union Uganda",                   "Money Remitter","2001","compliant",14),
    _nonbank("MONEYGRAM_UG",    "MoneyGram Uganda",                       "Money Remitter","2002","compliant",21),
    _nonbank("SENDWAVE_UG",     "Sendwave (Zepz Group) Uganda",           "Money Remitter","2021","compliant",12),
    _nonbank("INSTAREM_UG",     "InstaReM Uganda Limited",                "Money Remitter","2022","compliant",10),
    _nonbank("NALA_UG",         "NALA Payments Uganda Limited",           "Money Remitter","2022","compliant",8),
    _nonbank("CHIPPER_UG",      "Chipper Cash Uganda Limited",            "Money Remitter","2020","compliant",16),
    _nonbank("ORION_REMIT_UG",  "Orion Remit Uganda Limited",             "Money Remitter","2023","compliant",6),
    _nonbank("PAYSEND_UG",      "Paysend Uganda Limited",                 "Money Remitter","2023","compliant",5),

    # ═════════════════════════════════════════════════════════════════════════
    # CREDIT REFERENCE BUREAUS (2)
    # FI (Credit Reference Bureau) Regulations 2022
    # ═════════════════════════════════════════════════════════════════════════
    _nonbank("METROPOL_CRB",   "Metropol Uganda Limited (CRB)",           "Credit Reference Bureau","2011","compliant",22,3),
    _nonbank("TRANSUNION_CRB", "TransUnion Uganda (CRB Africa Registrar)","Credit Reference Bureau","2014","compliant",30,3),

    # ═════════════════════════════════════════════════════════════════════════
    # LARGE SACCOs — BOU Supervised (MDI Registered Societies Regs 2023)
    # Threshold: voluntary savings > UGX 1.5B OR institutional capital > UGX 500M
    # ═════════════════════════════════════════════════════════════════════════
    _nonbank("WAZALENDO_SACCO", "Wazalendo SACCO (UPDF)",                 "Large SACCO (BOU Supervised)","2025","compliant",7,3),
    _nonbank("CBS_PEWOSA",      "CBS PEWOSA SACCO",                       "Large SACCO (BOU Supervised)","2025","compliant",5,3),
    _nonbank("PARLIAMENT_SACCO","Uganda Parliamentary SACCO",             "Large SACCO (BOU Supervised)","2025","compliant",4,3),
    _nonbank("SHUUKU_SACCO",    "Shuuku SACCO",                           "Large SACCO (BOU Supervised)","2025","compliant",6,3,hq="Sheema"),
    _nonbank("TEACHERS_SACCO",  "Uganda Teachers SACCO",                  "Large SACCO (BOU Supervised)","2025","compliant",3,3),

    # ═════════════════════════════════════════════════════════════════════════
    # FOREX BUREAUX (200+; established bureaux)
    # Foreign Exchange Act 2004 + FX (Forex Bureaus & Money Remittance) Regs 2006
    # Min paid-up capital: UGX 20 million | Annual licence renewal required
    # Empire Forex Bureau: licence NOT renewed (BOU press release 2025)
    # ═════════════════════════════════════════════════════════════════════════
    _nonbank("METROPOLITAN_FXB", "Metropolitan Forex Bureau Ltd",         "Forex Bureau","1990","compliant",28),
    _nonbank("KAMWE_FXB",        "Kamwe Forex Bureau Ltd",                "Forex Bureau","2013","compliant",22),
    _nonbank("GUILD_FRANK_FXB",  "Guild Frank Forex Bureau Ltd",          "Forex Bureau","2005","compliant",35),
    _nonbank("LACEDRI_FXB",      "Lacedri Forex Bureau Ltd",              "Forex Bureau","2003","compliant",44),
    _nonbank("JETSET_FXB",       "Jetset Forex Bureau Ltd",               "Forex Bureau","2007","compliant",31),
    _nonbank("NORFRAX_FXB",      "Norfrax Forex Bureau Ltd",              "Forex Bureau","2001","compliant",18),
    _nonbank("DOLLAR_HOUSE_FXB", "Dollar House Forex Bureau Ltd",         "Forex Bureau","2006","compliant",40),
    _nonbank("DAHABSHIIL_FXB",   "Dahabshiil Forex Bureau Ltd",          "Forex Bureau","2004","compliant",25),
    _nonbank("ASIAN_OVERSEAS",   "Asian Overseas Exchange Limited",       "Forex Bureau","1999","compliant",38),
    _nonbank("BAKAAL_FXB",       "Bakaal Forex Bureau Limited",           "Forex Bureau","2002","compliant",52),
    _nonbank("JOSCA_FXB",        "Josca Forex Bureau Ltd",                "Forex Bureau","2008","compliant",29),
    _nonbank("HOTEL_AFRICANA_FXB","Hotel Africana Forex Bureau",          "Forex Bureau","1997","compliant",33),
    _nonbank("KW_FXB",           "KW Forex Bureau Ltd",                   "Forex Bureau","2010","compliant",21),
    _nonbank("CAPITAL_FXB",      "Capital Forex Bureau",                  "Forex Bureau","2005","compliant",47),
    _nonbank("DOTCOM_FXB",       "Dotcom Forex Bureau",                   "Forex Bureau","2003","compliant",36),
    _nonbank("BIGBILLS_FXB",     "Bigbills FXB Ltd",                      "Forex Bureau","2011","compliant",28),
    _nonbank("ENTEBBE_FXB",      "Entebbe Forex Bureau Ltd",              "Forex Bureau","2009","compliant",42,hq="Entebbe"),
    _nonbank("JUBA_EXPRESS_FXB", "Juba Express Forex Bureau Ltd",         "Forex Bureau","2012","compliant",30),
    _nonbank("MUNGULENI_FXB",    "Munguleni Forex Bureau Limited",        "Forex Bureau","2013","compliant",25,hq="Arua"),
    _nonbank("EMMAN_FOREX",      "Emmanual Forex De-Change Limited",      "Forex Bureau","2010","compliant",55),
    _nonbank("HIS_GRACE_FXB",    "His Grace Forex Bureau Limited",        "Forex Bureau","2015","compliant",60,hq="Entebbe"),
    _nonbank("OPEN_FXB",         "Open Forex Bureau Limited",             "Forex Bureau","2014","compliant",19),
    _nonbank("DAWINTA_FXB",      "Dawinta Forex Bureau Limited",          "Forex Bureau","2012","compliant",37),
    _nonbank("ABEDIS_FXB",       "Abedis Forex Bureau Limited",           "Forex Bureau","2016","compliant",29),
    _nonbank("ELBA_FXB",         "Elba FXB Ltd",                          "Forex Bureau","2009","compliant",41),
    _nonbank("NURM_FXB",         "NURM Forex Bureau Ltd",                 "Forex Bureau","2008","compliant",33),
    _nonbank("AMAL_FXB",         "Amal Forex Bureau Limited",             "Forex Bureau","2010","compliant",27),
    _nonbank("ACCESS_FXB",       "Access FXB Kabalagala",                 "Forex Bureau","2011","compliant",45),
    _nonbank("AHAD_FXB",         "Ahad Forex Bureau Ltd",                 "Forex Bureau","2014","compliant",32),
    _nonbank("AKRA_CASH",        "AKRA Cash Forex Bureau",                "Forex Bureau","2015","compliant",50),
    _nonbank("ALPHA_CAPITAL_FXB","Alpha Capital Partners Forex Bureau",   "Forex Bureau","2016","compliant",23),
    _nonbank("AMA_CASH_FXB",     "AMA Cash Forex Bureau Limited",         "Forex Bureau","2013","compliant",38),
    _nonbank("AMRON_FXB",        "Amron Forex Bureau",                    "Forex Bureau","2012","compliant",44,hq="Mbarara"),
    _nonbank("APPLE_CASH_FXB",   "Apple Cash Forex Bureau Ltd",           "Forex Bureau","2017","compliant",26),
    _nonbank("ASANTE_FXB",       "Asante Forex Bureau Limited",           "Forex Bureau","2008","compliant",53),
    _nonbank("ASHANTI_FXB",      "Ashanti Forex Bureau Ltd",              "Forex Bureau","2007","compliant",39),
    _nonbank("ASSURED_FXB",      "Assured Forex Bureau Limited",          "Forex Bureau","2012","compliant",31),
    _nonbank("ATELERE_FXB",      "Atelere Forex Bureau Limited",          "Forex Bureau","2014","compliant",47),
    _nonbank("AUSSIE_FXB",       "Aussie Forex Bureau Ltd",               "Forex Bureau","2016","compliant",36),
    _nonbank("BAIKA_FXB",        "Baika Forex Bureau",                    "Forex Bureau","2011","compliant",28,hq="Mbarara"),
    _nonbank("BANKENS_FXB",      "Bankens Forex Bureau Ltd",              "Forex Bureau","2013","compliant",42),
    _nonbank("BANXELL_FXB",      "Banxell Forex Bureau Ltd",              "Forex Bureau","2018","compliant",22),
    _nonbank("BCL_EXCHANGE",     "BCL Exchange Bureau de Change Limited", "Forex Bureau","2015","compliant",55),
    _nonbank("BERLIN_FXB",       "Berlin Forex Bureau Limited",           "Forex Bureau","2017","compliant",30),
    _nonbank("BEST_FXB",         "Best Forex Bureau",                     "Forex Bureau","2009","compliant",48),
    _nonbank("BEST_RATES_FXB",   "Best Rates Forex Bureau Limited",       "Forex Bureau","2014","compliant",37),
    _nonbank("BICCO_FXB",        "Bicco Forex Bureau Limited",            "Forex Bureau","2010","compliant",43),
    _nonbank("BIOS_FXB",         "BIOS Forex Bureau Limited",             "Forex Bureau","2013","compliant",24),
    _nonbank("BLUEPRINT_FXB",    "Blue Print Forex Bureau",               "Forex Bureau","2016","compliant",29),
    _nonbank("BOLD_FXB",         "Bold Forex Bureau Limited",             "Forex Bureau","2015","compliant",51),
    _nonbank("BRAVE_FXB",        "Brave Forex Bureau Limited",            "Forex Bureau","2018","compliant",33),
    _nonbank("BUDGET_FXB",       "Budget Forex Bureau",                   "Forex Bureau","2007","compliant",46),
    _nonbank("BULSHO_FXB",       "Bulsho Express Forex Bureau & Money Transfer","Forex Bureau","2011","compliant",27),
    _nonbank("CASHMART_FXB",     "Cashmart Forex Bureau",                 "Forex Bureau","2008","compliant",40),
    _nonbank("CASHCITY_FXB",     "Cashcity Forex Bureau Limited",         "Forex Bureau","2014","compliant",25),
    _nonbank("CASHFLOW_FXB",     "Cash Flow Forex Bureau Kikubo",         "Forex Bureau","2013","compliant",58),
    _nonbank("CITY_FXB",         "City FXB Ltd",                          "Forex Bureau","2010","compliant",34),
    _nonbank("CIVIC_FXB",        "Civic Forex Bureau",                    "Forex Bureau","2012","compliant",62),
    _nonbank("COMDEL_FXB",       "Comdel Forex Bureau",                   "Forex Bureau","2009","compliant",44),
    _nonbank("CORNICHE_FXB",     "Corniche Forex Bureau Limited",         "Forex Bureau","2015","compliant",19),
    _nonbank("COURTEOUS_FXB",    "Courteous Forex Bureau Limited",        "Forex Bureau","2016","compliant",38),
    _nonbank("DESERT_EXCHANGE",  "Desert Exchange Forex Bureau",          "Forex Bureau","2011","compliant",56),
    _nonbank("DIVINE_CASH_FXB",  "Divine Cash Forex Bureau",              "Forex Bureau","2013","compliant",48),
    _nonbank("DOSHI_FOREX",      "Doshi Forex Limited",                   "Forex Bureau","2006","compliant",35),
    _nonbank("DUAL_FXB",         "Dual Forex Bureau",                     "Forex Bureau","2014","compliant",43),
    _nonbank("ECONOMIC_EXCHANGE","Economic Exchange Forex Bureau",        "Forex Bureau","2010","compliant",27),
    _nonbank("ELDOUMA_FXB",      "Eldouma Forex Bureau Limited",          "Forex Bureau","2012","compliant",32),
    _nonbank("ELINET_FXB",       "Elinet Forex Bureau Limited",           "Forex Bureau","2015","compliant",41),
    _nonbank("EPIC_FXB",         "Epic Forex Bureau Limited",             "Forex Bureau","2017","compliant",24),
    _nonbank("FAIR_PRICE_FXB",   "Fair Price Forex Bureau Limited",       "Forex Bureau","2011","compliant",37),
    _nonbank("FIN_FINEE_FXB",    "Fin Finee Forex Bureau Limited",        "Forex Bureau","2016","compliant",30),
    _nonbank("FLEX_FXB",         "Flex Forex Bureau Limited",             "Forex Bureau","2018","compliant",22),
    _nonbank("FOREPLEX_FXB",     "Foreplex Bureau De Change",             "Forex Bureau","2013","compliant",46),
    _nonbank("FRIENDS_FXB",      "Friends Forex Bureau",                  "Forex Bureau","2009","compliant",53),
    _nonbank("GAI_EXCHANGE",     "Gai Exchange Forex Bureau Limited",     "Forex Bureau","2014","compliant",29),
    _nonbank("GEORGECOM_FXB",    "Georgecom Forex Bureau",                "Forex Bureau","2016","compliant",35),
    _nonbank("GLORY_FXB",        "Glory Forex Bureau Limited",            "Forex Bureau","2012","compliant",48),
    _nonbank("HABARI_FXB",       "Habari Forex Bureau Limited",           "Forex Bureau","2015","compliant",26),
    _nonbank("HADY_FXB",         "Hady Forex Bureau Nakivubo",            "Forex Bureau","2010","compliant",40),
    _nonbank("HARVAN_FXB",       "Harvan Forex Bureau Limited",           "Forex Bureau","2013","compliant",33),
    _nonbank("HEAVEN_GATES_FXB", "Heaven Gates Forex Bureau",             "Forex Bureau","2014","compliant",57),
    _nonbank("HIGH_SAVINGS_FXB", "High Savings Forex Bureau Limited",     "Forex Bureau","2011","compliant",44),
    _nonbank("HOMELAND_FXB",     "Homeland Forex Bureau Limited",         "Forex Bureau","2017","compliant",20),
    _nonbank("HOPE_FXB",         "Hope Forex Bureau Limited",             "Forex Bureau","2013","compliant",38),
    _nonbank("HORIZON_FXB",      "Horizon Forex Bureau Limited",          "Forex Bureau","2012","compliant",51),
    _nonbank("HYDERY_FXB",       "Hydery FXB",                            "Forex Bureau","2009","compliant",45),
    _nonbank("IFTIN_FXB",        "Iftin Forex Bureau Limited",            "Forex Bureau","2011","compliant",36),
    _nonbank("INSTA_REMIT_FXB",  "Insta Remit Limited",                   "Forex Bureau","2016","compliant",28),
    _nonbank("JABRIL_FXB",       "Jabril Forex Bureau Limited",           "Forex Bureau","2014","compliant",42),
    _nonbank("JAMA_FXB",         "Jama Forex Bureau Ltd",                 "Forex Bureau","2010","compliant",55),
    _nonbank("JB_STAR_FXB",      "JB Star Forex Bureau",                  "Forex Bureau","2015","compliant",31,hq="Entebbe"),
    _nonbank("JENTU_FXB",        "Jentu Forex Bureau Ltd",                "Forex Bureau","2012","compliant",47),
    _nonbank("JIMMIE_FXB",       "Jimmie Forex Bureau Limited",           "Forex Bureau","2013","compliant",23),
    _nonbank("JINJA_FXB",        "Jinja Forex Bureau Limited",            "Forex Bureau","2008","compliant",59,hq="Jinja"),
    _nonbank("JOEX_FXB",         "Joex Forex Bureau",                     "Forex Bureau","2011","compliant",34),
    _nonbank("JOPPA_FXB",        "Joppa Exchange Services Limited",       "Forex Bureau","2017","compliant",25),
    _nonbank("JOSHUATEC_FXB",    "Joshuatec Forex Bureau Ltd",            "Forex Bureau","2014","compliant",40,hq="Entebbe"),
    _nonbank("JOTEM_FXB",        "Jotem FXB Limited",                     "Forex Bureau","2018","compliant",18),
    _nonbank("KAKA_FXB",         "Kaka Forex Bureau",                     "Forex Bureau","2016","compliant",29),
    _nonbank("KASE_FXB",         "Kase Forex Bureau Ltd",                 "Forex Bureau","2015","compliant",43),
    _nonbank("KIKUUBO_LANE_FXB", "Kikuubo Lane Forex Bureau Ltd",         "Forex Bureau","2013","compliant",37),
    _nonbank("KLYN_CASH_FXB",    "Klyn Cash Forex Bureau Ltd",            "Forex Bureau","2017","compliant",22),
    _nonbank("KOMADELA_FXB",     "Komadela Forex Bureau Limited",         "Forex Bureau","2015","compliant",48,hq="Kitgum"),
    _nonbank("KREM_FXB",         "Krem Reliable Forex Bureau Limited",    "Forex Bureau","2012","compliant",35),
    _nonbank("LACRUCHE_FXB",     "Lacruche Forex Bureau Limited",         "Forex Bureau","2014","compliant",52),
    _nonbank("LAMA_FXB",         "Lama Forex Bureau Ltd",                 "Forex Bureau","2013","compliant",27),
    _nonbank("LEGACY_FOREX",     "Legacy Forex Uganda Limited",           "Forex Bureau","2010","compliant",44),
    _nonbank("LOMS_FXB",         "Loms Forex Bureau",                     "Forex Bureau","2011","compliant",38),
    _nonbank("LUKS_FXB",         "Luks Forex Bureau Limited",             "Forex Bureau","2015","compliant",31),
    _nonbank("MAALUM_FXB",       "Maalum Forex Bureau Limited",           "Forex Bureau","2013","compliant",56),
    _nonbank("MACH_FXB",         "Mach Forex Bureau",                     "Forex Bureau","2009","compliant",42),
    _nonbank("MANDWA_FXB",       "Mandwa Forex Bureau Limited",           "Forex Bureau","2016","compliant",24),
    _nonbank("METANIK_FXB",      "Metanik Forex Bureau Limited",          "Forex Bureau","2014","compliant",36),
    _nonbank("MIDLAND_FXB",      "Midland Forex Bureau",                  "Forex Bureau","2007","compliant",60),
    _nonbank("MID_WEST_FXB",     "Mid-West Forex Bureau",                 "Forex Bureau","2010","compliant",45),
    _nonbank("MONEY_LAND_FXB",   "Money Land Forex Bureau",               "Forex Bureau","2012","compliant",29),
    _nonbank("MUGIZ_FXB",        "Mugiz Forex Bureau Limited",            "Forex Bureau","2015","compliant",53),
    _nonbank("MULORA_FXB",       "Mulora Forex Bureau Limited",           "Forex Bureau","2016","compliant",20),
    _nonbank("MUNA_FXB",         "Muna Forex Bureau",                     "Forex Bureau","2011","compliant",47,hq="Kabale"),
    _nonbank("MUNTU_FXB",        "Muntu Bureau De Change Limited",        "Forex Bureau","2013","compliant",33,hq="Entebbe"),
    _nonbank("MUVULE_FXB",       "Muvule Forex Bureau Limited",           "Forex Bureau","2014","compliant",41),
    _nonbank("NEW_MONEY_FXB",    "New Money Forex Bureau",                "Forex Bureau","2012","compliant",27),
    _nonbank("NGAMBI_FXB",       "Ngambi Forex Bureau Limited",           "Forex Bureau","2015","compliant",36),
    _nonbank("NICOS_FXB",        "Nicos Forex Bureau Limited",            "Forex Bureau","2013","compliant",50),
    _nonbank("NOOR_FXB",         "Noor Forex Bureau",                     "Forex Bureau","2010","compliant",43),
    _nonbank("NTUNA_FXB",        "Ntuna Forex Bureau Limited",            "Forex Bureau","2017","compliant",22),
    _nonbank("ODAA_FXB",         "Odaa Forex Bureau",                     "Forex Bureau","2013","compliant",39),
    _nonbank("OLOMPIC_FXB",      "Olompic Forex Bureau",                  "Forex Bureau","2011","compliant",45),
    _nonbank("OLOMPIC2_FXB",     "Olompic Forex Bureau (King Fahd Plaza)","Forex Bureau","2014","compliant",50),
    _nonbank("FOREX2000_FXB",    "Forex Bureau 2000 Limited",             "Forex Bureau","2003","compliant",62),
    # Revoked — Empire Forex Bureau (BOU press release 2025)
    _nonbank("EMPIRE_FXB",       "Empire Forex Bureau",                   "Forex Bureau","2008","non_compliant",220,1,False,False,"Kampala","revoked"),
    # New entrants 2024–2026
    _nonbank("AYOPESA_FXB",      "Ayopesa Forex Bureau Limited",          "Forex Bureau","2024","compliant",8),
    _nonbank("BEYOND_BOARDS_FXB","Beyond Boarders Forex Bureau Limited",  "Forex Bureau","2024","compliant",12),
    _nonbank("BULALE_FXB",       "Bulale Forex Bureau Limited",           "Forex Bureau","2025","compliant",3),
    _nonbank("CARLOSO_FXB",      "Carloso Forex Bureau Limited",          "Forex Bureau","2024","compliant",15),
    _nonbank("CARLYLE_FXB",      "Carlyle Forex Bureau Limited",          "Forex Bureau","2025","compliant",5),
    _nonbank("CASHFIELD_FXB",    "Cashfield Forex Bureau Limited",        "Forex Bureau","2025","compliant",7),
    _nonbank("ECCENTRIC_FXB",    "Eccentric Links Forex Bureau Limited",  "Forex Bureau","2024","compliant",11),
    _nonbank("ELEAZAR_FXB",      "Eleazar Forex Bureau Limited",          "Forex Bureau","2024","compliant",14),
    _nonbank("DEELLA_FXB",       "Deella Forex Bureau Limited",           "Forex Bureau","2025","compliant",6),
    _nonbank("DOWIETU_FXB",      "Dowietu Forex Bureau Limited",          "Forex Bureau","2024","compliant",9,hq="Nansana"),
    _nonbank("GAINFUL_FXB",      "Gainful Exchange Forex Bureau Limited", "Forex Bureau","2025","compliant",4),
    _nonbank("KANDE_FXB",        "Kande Forex Bureau Limited",            "Forex Bureau","2024","compliant",16),
    _nonbank("LAMONNAIE_FXB",    "Lamonnaie Forex Bureau",                "Forex Bureau","2024","compliant",10,hq="Wakiso"),
    _nonbank("LE_CENT_FXB",      "Le Cent Forex Bureau Limited",          "Forex Bureau","2025","compliant",2),
    _nonbank("LIMERK_FXB",       "Limerk Forex Bureau Limited",           "Forex Bureau","2025","compliant",1),
    _nonbank("LISHANA_FXB",      "Lishana Forex Bureau Limited",          "Forex Bureau","2024","compliant",18,hq="Gayaza"),
    _nonbank("MALIVI_FXB",       "Malivi Forex Bureau Limited",           "Forex Bureau","2024","compliant",13),
    _nonbank("MEZOR_FXB",        "Mezor Forex Bureau Limited",            "Forex Bureau","2024","compliant",17),
    _nonbank("MOJO_FXB",         "Mojo Forex Bureau Limited",             "Forex Bureau","2025","compliant",3),
    _nonbank("MUKA_FXB",         "Muka Forex Bureau",                     "Forex Bureau","2024","compliant",20),
    _nonbank("MYFXCHOICE_FXB",   "Myfxchoice Forex Bureau Limited",      "Forex Bureau","2024","compliant",15),
    _nonbank("NEW_SHORES_FXB",   "New Shores Forex Bureau Limited",       "Forex Bureau","2025","compliant",8,hq="Namanve"),
    _nonbank("NIVARAL_FXB",      "Nivaral Forex Bureau Limited",          "Forex Bureau","2024","compliant",11),
    _nonbank("ABISELOM_FXB",     "Abiselom Forex Bureau Limited",         "Forex Bureau","2025","compliant",5),
    _nonbank("AVO_CASH_FXB",     "Avo Cash Forex Bureau Limited",         "Forex Bureau","2025","compliant",4,hq="Arua"),
    _nonbank("BAIKA2_FXB",       "Baika Forex Bureau (Mbarara Branch)",   "Forex Bureau","2024","compliant",19,hq="Mbarara"),
    _nonbank("BATA_FXB",         "Bata Forex Bureau",                     "Forex Bureau","2024","compliant",13,hq="Arua"),
    _nonbank("BEVAR_FXB",        "Bevar Forex Bureau Limited",            "Forex Bureau","2024","compliant",22),
    _nonbank("BHRIN_FXB",        "Bhrin Forex Bureau Ltd",                "Forex Bureau","2025","compliant",7),
    _nonbank("BIGCHIEF_FXB",     "Bigchief Unit Forex Bureau Limited",    "Forex Bureau","2024","compliant",16,hq="Iganga"),
    _nonbank("BUDDU_FXB",        "Buddu Forex Bureau Limited",            "Forex Bureau","2024","compliant",21),
    _nonbank("BUYI_FXB",         "Buyi Forex Bureau Limited",             "Forex Bureau","2025","compliant",9),
    _nonbank("CASH_CAGE_FXB",    "Cash Cage Forex Bureau Limited",        "Forex Bureau","2024","compliant",14,hq="Mengo"),
    _nonbank("CASH_GALLERY_FXB", "Cash Gallery Forex Bureau Limited",     "Forex Bureau","2025","compliant",6),
    _nonbank("CASH_OUT_FXB",     "Cash Out Forex Bureau Limited",         "Forex Bureau","2024","compliant",18,hq="Kabale"),
    _nonbank("CASH_PEAK_FXB",    "Cash Peak Forex Bureau Limited",        "Forex Bureau","2025","compliant",3),
    _nonbank("CLYDE_FXB",        "Clyde Forex Bureau",                    "Forex Bureau","2024","compliant",25,hq="Jinja"),
    _nonbank("CRATER_FXB",       "Crater Forex Bureau Limited",           "Forex Bureau","2024","compliant",12),
    _nonbank("DEMO_FXB",         "Demo FXB",                              "Forex Bureau","2024","compliant",20,hq="Fort Portal"),
    _nonbank("DESTINY_FXB",      "Destiny Forex Bureau Ltd",              "Forex Bureau","2025","compliant",8),
    _nonbank("DHAHAB_FXB",       "Dhahab International Forex Bureau",     "Forex Bureau","2025","compliant",4),
    _nonbank("DON_FXB",          "Don Forex Bureau Limited",              "Forex Bureau","2024","compliant",17),
    _nonbank("IDAA_FXB",         "Idaa FXB",                              "Forex Bureau","2025","compliant",9,hq="Busia"),
    _nonbank("INTERLINK_FXB",    "Interlink FXB",                         "Forex Bureau","2024","compliant",23,hq="Jinja"),
    _nonbank("JACKSHANE_FXB",    "Jackshane Forex Bureau Limited",        "Forex Bureau","2024","compliant",11),
    _nonbank("JARNAZ_FXB",       "Jarnaz Forex Bureau Ltd",               "Forex Bureau","2025","compliant",5),
    _nonbank("JEEN_MATA_FXB",    "Jeen Mata Forex Bureau Limited",        "Forex Bureau","2025","compliant",7),
    _nonbank("JINEX_FXB",        "Jinex Forex Bureau Limited",            "Forex Bureau","2024","compliant",19),
    _nonbank("J_SUPI_FXB",       "J Supi Kampala Road Forex Bureau Ltd",  "Forex Bureau","2024","compliant",15),
    _nonbank("KOINE_FXB",        "Koine Forex Bureau Ltd",                "Forex Bureau","2025","compliant",6),
    _nonbank("LACEDRI2_FXB",     "Lacedri Forex Bureau (Kireka Branch)",  "Forex Bureau","2019","compliant",30,hq="Kireka"),
    _nonbank("LYJOREPH_FXB",     "Lyjoreph Forex Bureau",                 "Forex Bureau","2024","compliant",14),
    _nonbank("MONEY_TREE_FXB",   "Money Tree Forex Bureau Limited",       "Forex Bureau","2024","compliant",10,hq="Entebbe"),
    _nonbank("MUSHALI_FXB",      "Mushali Exchange Forex Bureau Limited", "Forex Bureau","2024","compliant",21),
    _nonbank("NOVO_FXB",         "Novo Forex Bureau",                     "Forex Bureau","2024","compliant",16,hq="Tororo"),
    _nonbank("AVO_CASH2_FXB",    "Avo Cash Forex Bureau (Arua Park)",     "Forex Bureau","2025","compliant",3),
]


def seed_institutions(db_session) -> int:
    """
    Idempotent seed — inserts only institutions that don't already exist.
    Returns count of newly inserted records.
    """
    from app.regulatory_models import Institution
    from app.compliance_engine import calculate_compliance_risk

    seeded = 0
    now = datetime.now(timezone.utc)

    for data in _INSTITUTIONS:
        code = data["institution_code"]
        if db_session.query(Institution).filter_by(institution_code=code).first():
            continue

        aml_days = data.pop("aml_days_ago", 30)
        aml_date = now - timedelta(days=aml_days)

        risk_score, risk_level, issues = calculate_compliance_risk(
            {**data, "aml_last_report_date": aml_date},
            fraud_stats={"fraud_rate": 0.0},
        )

        inst = Institution(
            institution_code=code,
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
    logger.info(f"✅ BOU institution seed complete: {seeded} new records")
    return seeded