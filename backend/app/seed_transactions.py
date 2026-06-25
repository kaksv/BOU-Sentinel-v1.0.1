"""
BOU Sentinel — Transaction Seed Data
Generates realistic historical transactions for all BOU-supervised institutions,
scored through the live Isolation Forest fraud model.

Account prefix convention (first 3 chars → institution):
  STB = Stanbic, CEN = Centenary, DFC = DFCU, ABS = Absa,
  SCB = StanChart, CTB = Citi, EQB = Equity, DTB = DTB,
  ECO = Ecobank, KCB = KCB, BOA = Bank of Africa,
  BRB = Baroda, BOI = Bank of India, CAI = Cairo (HIGH-RISK),
  EXI = Exim, HFB = HFB, NCB = NCBA, IMB = I&M,
  SLM = Salaam, TRO = Tropical, UBA = UBA, PLB = Pearl,
  ABC = ABC Capital, GTB = GTB (MEDIUM-RISK), OPP = Opportunity,
  YKB = Yako (CRITICAL-RISK), BRC = BRAC, FTB = Finance Trust,
  PRB = Pride Bank, FIN = FINCA MDI, PRM = PRIDE MDI, UGA = UGAFODE,
  MTN = MTN MoMo, ATL = Airtel Money

Run once after seeding institutions:
  curl -X POST http://localhost:8000/api/transactions/seed
"""
import uuid
import logging
import random
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger("bou-sentinel.seed_transactions")

# ─────────────────────────────────────────────────────────────────────────────
# ACCOUNT POOLS PER INSTITUTION
# ─────────────────────────────────────────────────────────────────────────────
# Maps institution prefix → list of realistic account number stubs
INSTITUTION_ACCOUNTS: dict[str, list[str]] = {
    # Tier I — Commercial Banks
    "STB": ["STB1000234", "STB2001456", "STB3002789", "STB4003901", "STB5004112"],
    "CEN": ["CEN1100234", "CEN2201456", "CEN3302789", "CEN4403901", "CEN5504112"],
    "DFC": ["DFC1010234", "DFC2020456", "DFC3030789", "DFC4040901", "DFC5050112"],
    "ABS": ["ABS1001234", "ABS2002456", "ABS3003789", "ABS4004901", "ABS5005112"],
    "SCB": ["SCB1100001", "SCB2200002", "SCB3300003", "SCB4400004", "SCB5500005"],
    "CTB": ["CTB1000111", "CTB2000222", "CTB3000333", "CTB4000444", "CTB5000555"],
    "EQB": ["EQB1001001", "EQB2002002", "EQB3003003", "EQB4004004", "EQB5005005"],
    "DTB": ["DTB1010101", "DTB2020202", "DTB3030303", "DTB4040404", "DTB5050505"],
    "ECO": ["ECO1111234", "ECO2221456", "ECO3331789", "ECO4441901", "ECO5552112"],
    "KCB": ["KCB1000001", "KCB2000002", "KCB3000003", "KCB4000004", "KCB5000005"],
    "BOA": ["BOA1234001", "BOA2345002", "BOA3456003", "BOA4567004", "BOA5678005"],
    "BRB": ["BRB1001234", "BRB2002456", "BRB3003789", "BRB4004901", "BRB5005112"],
    "BOI": ["BOI1100001", "BOI2200002", "BOI3300003", "BOI4400004", "BOI5500005"],
    "CAI": ["CAI1000001", "CAI2000002", "CAI3000003", "CAI4000004", "CAI5000005"],  # HIGH-RISK
    "EXI": ["EXI1001001", "EXI2002002", "EXI3003003", "EXI4004004", "EXI5005005"],
    "HFB": ["HFB1100234", "HFB2200456", "HFB3300789", "HFB4400901", "HFB5500112"],
    "NCB": ["NCB1001234", "NCB2002456", "NCB3003789", "NCB4004901", "NCB5005112"],
    "IMB": ["IMB1000001", "IMB2000002", "IMB3000003", "IMB4000004", "IMB5000005"],
    "SLM": ["SLM1001234", "SLM2002456", "SLM3003789", "SLM4004901", "SLM5005112"],
    "TRO": ["TRO1000001", "TRO2000002", "TRO3000003", "TRO4000004", "TRO5000005"],
    "UBA": ["UBA1001001", "UBA2002002", "UBA3003003", "UBA4004004", "UBA5005005"],
    "PLB": ["PLB1000234", "PLB2000456", "PLB3000789", "PLB4000901", "PLB5001112"],
    # Tier II — Credit Institutions
    "ABC": ["ABC1001234", "ABC2002456", "ABC3003789", "ABC4004901", "ABC5005112"],
    "GTB": ["GTB1000001", "GTB2000002", "GTB3000003", "GTB4000004", "GTB5000005"],  # MEDIUM
    "OPP": ["OPP1001001", "OPP2002002", "OPP3003003", "OPP4004004", "OPP5005005"],
    "YKB": ["YKB1000001", "YKB2000002", "YKB3000003", "YKB4000004", "YKB5000005"],  # CRITICAL
    "BRC": ["BRC1001234", "BRC2002456", "BRC3003789", "BRC4004901", "BRC5005112"],
    "FTB": ["FTB1000001", "FTB2000002", "FTB3000003", "FTB4000004", "FTB5000005"],
    "PRB": ["PRB1001234", "PRB2002456", "PRB3003789", "PRB4004901", "PRB5005112"],
    # Tier III — MDIs
    "FIN": ["FIN1001001", "FIN2002002", "FIN3003003", "FIN4004004", "FIN5005005"],
    "PRM": ["PRM1001234", "PRM2002456", "PRM3003789", "PRM4004901", "PRM5005112"],
    "UGA": ["UGA1000001", "UGA2000002", "UGA3000003", "UGA4000004", "UGA5000005"],
    # Non-Bank PSPs
    "MTN": ["MTN2567001", "MTN2567002", "MTN2567003", "MTN7891004", "MTN7891005"],
    "ATL": ["ATL0701001", "ATL0701002", "ATL0701003", "ATL0312004", "ATL0312005"],
}

# Ugandan locations for realistic distribution
DOMESTIC_LOCATIONS = [
    "Kampala", "Kampala", "Kampala",  # weighted heavily
    "Entebbe", "Jinja", "Mbarara", "Gulu", "Mbale",
    "Kasese", "Fort Portal", "Kabale", "Lira", "Arua",
    "Masaka", "Soroti", "Tororo", "Hoima", "Busia",
]

INTERNATIONAL_LOCATIONS = [
    "Nairobi", "Lagos", "London", "Dubai", "Dar es Salaam",
    "Kigali", "Johannesburg", "New York", "Beijing", "Mumbai",
]

TRANSACTION_TYPES = ["transfer", "deposit", "withdrawal", "payment", "internal_transfer"]

# Device IDs and IPs for realism
DEVICE_IDS = [f"DEV-{i:06d}" for i in range(1, 201)]
IP_POOL = [
    f"41.210.{random.randint(1,254)}.{random.randint(1,254)}" for _ in range(50)
] + [
    f"197.157.{random.randint(1,254)}.{random.randint(1,254)}" for _ in range(30)
] + [
    f"41.74.{random.randint(1,254)}.{random.randint(1,254)}" for _ in range(20)
]


# ─────────────────────────────────────────────────────────────────────────────
# TRANSACTION PROFILE BY INSTITUTION RISK LEVEL
# Cairo (HIGH) and Yako (CRITICAL) get elevated fraud patterns
# ─────────────────────────────────────────────────────────────────────────────
INSTITUTION_PROFILES = {
    # prefix: (normal_amount_range, fraud_rate, international_rate, off_hours_rate)
    "STB": (50_000,    10_000_000,  0.01, 0.05, 0.08),
    "CEN": (30_000,     5_000_000,  0.01, 0.04, 0.07),
    "DFC": (40_000,     8_000_000,  0.01, 0.05, 0.08),
    "ABS": (100_000,   15_000_000,  0.01, 0.06, 0.07),
    "SCB": (500_000,   50_000_000,  0.01, 0.10, 0.06),
    "CTB": (1_000_000, 80_000_000,  0.01, 0.15, 0.06),
    "EQB": (20_000,     3_000_000,  0.02, 0.04, 0.10),
    "DTB": (50_000,    10_000_000,  0.01, 0.06, 0.08),
    "ECO": (30_000,     5_000_000,  0.02, 0.05, 0.09),
    "KCB": (50_000,    10_000_000,  0.01, 0.05, 0.08),
    "BOA": (40_000,     8_000_000,  0.02, 0.05, 0.09),
    "BRB": (100_000,   20_000_000,  0.01, 0.08, 0.07),
    "BOI": (100_000,   15_000_000,  0.02, 0.07, 0.08),
    "CAI": (50_000,    20_000_000,  0.12, 0.25, 0.20),  # HIGH-RISK: many suspicious
    "EXI": (100_000,   20_000_000,  0.01, 0.07, 0.08),
    "HFB": (50_000,     8_000_000,  0.01, 0.04, 0.08),
    "NCB": (30_000,     5_000_000,  0.01, 0.04, 0.08),
    "IMB": (100_000,   15_000_000,  0.01, 0.06, 0.07),
    "SLM": (30_000,     5_000_000,  0.02, 0.05, 0.09),
    "TRO": (30_000,     5_000_000,  0.02, 0.05, 0.09),
    "UBA": (50_000,    10_000_000,  0.02, 0.06, 0.09),
    "PLB": (30_000,     5_000_000,  0.02, 0.05, 0.10),
    "ABC": (20_000,     3_000_000,  0.02, 0.04, 0.10),
    "GTB": (20_000,     3_000_000,  0.06, 0.12, 0.15),  # MEDIUM-RISK
    "OPP": (10_000,     1_000_000,  0.02, 0.04, 0.10),
    "YKB": (10_000,     2_000_000,  0.18, 0.35, 0.30),  # CRITICAL: high fraud
    "BRC": (10_000,     1_000_000,  0.02, 0.04, 0.10),
    "FTB": (10_000,     1_500_000,  0.02, 0.04, 0.10),
    "PRB": (10_000,     1_000_000,  0.02, 0.04, 0.10),
    "FIN": (5_000,        500_000,  0.02, 0.03, 0.10),
    "PRM": (5_000,        500_000,  0.02, 0.03, 0.10),
    "UGA": (5_000,        500_000,  0.02, 0.03, 0.10),
    "MTN": (1_000,      2_000_000,  0.03, 0.04, 0.12),
    "ATL": (1_000,      1_500_000,  0.03, 0.04, 0.12),
}


def _random_account(prefix: str, exclude: Optional[str] = None) -> str:
    """Pick a random account for a given prefix, optionally excluding one."""
    pool = INSTITUTION_ACCOUNTS.get(prefix, [f"{prefix}9999999"])
    choices = [a for a in pool if a != exclude] or pool
    return random.choice(choices)


def _random_receiver_prefix(sender_prefix: str) -> str:
    """Pick a receiver institution prefix (can be same or different bank)."""
    all_prefixes = list(INSTITUTION_ACCOUNTS.keys())
    # 60 % same institution, 40 % different
    if random.random() < 0.6:
        return sender_prefix
    return random.choice([p for p in all_prefixes if p != sender_prefix])


def generate_transactions(n: int = 500, days_back: int = 30) -> list[dict]:
    """
    Generate `n` realistic synthetic transactions spread over the last `days_back` days.
    Each dict matches the TransactionCreate schema exactly.
    """
    random.seed(42)
    now = datetime.now(timezone.utc)
    transactions = []
    prefixes = list(INSTITUTION_PROFILES.keys())

    for i in range(n):
        prefix = random.choice(prefixes)
        profile = INSTITUTION_PROFILES[prefix]
        min_amt, max_amt, fraud_rate, intl_rate, off_hours_rate = profile

        # Timestamp — spread uniformly over past `days_back` days
        seconds_back = random.randint(0, days_back * 86400)
        ts = now - timedelta(seconds=seconds_back)

        # Off-hours weighting
        hour = ts.hour
        is_off_hours = hour < 6 or hour > 22
        if random.random() < off_hours_rate and not is_off_hours:
            # Force an off-hours tx for high-risk institutions
            ts = ts.replace(hour=random.randint(0, 5))
            is_off_hours = True

        # Amount
        is_high_value_tx = random.random() < fraud_rate
        if is_high_value_tx:
            amount = random.uniform(max_amt * 0.8, max_amt * 5)
        else:
            amount = random.uniform(min_amt, max_amt)
        amount = round(amount, 0)

        # Location
        is_international = random.random() < intl_rate
        if is_international:
            location = random.choice(INTERNATIONAL_LOCATIONS)
        else:
            location = random.choice(DOMESTIC_LOCATIONS)

        # Transaction type — withdrawals more common in high-risk
        if is_high_value_tx or is_off_hours:
            tx_type = random.choices(
                TRANSACTION_TYPES,
                weights=[0.35, 0.05, 0.40, 0.15, 0.05], k=1
            )[0]
        else:
            tx_type = random.choices(
                TRANSACTION_TYPES,
                weights=[0.40, 0.25, 0.20, 0.13, 0.02], k=1
            )[0]

        sender = _random_account(prefix)
        receiver_prefix = _random_receiver_prefix(prefix)
        receiver = _random_account(receiver_prefix, exclude=sender)

        transactions.append({
            "transaction_id": f"TXN-{uuid.uuid4().hex[:12].upper()}",
            "sender_account":  sender,
            "receiver_account": receiver,
            "amount": amount,
            "transaction_type": tx_type,
            "location": location,
            "device_id": random.choice(DEVICE_IDS),
            "ip_address": random.choice(IP_POOL),
            "timestamp": ts.isoformat(),
        })

    return transactions

# ─────────────────────────────────────────────────────────────────────────────
# EXPLICIT FRAUD TRANSACTION PATTERNS
# These are hardcoded as fraud — they do not go through the model scorer.
# Patterns mirror real BOU-documented fraud typologies.
# ─────────────────────────────────────────────────────────────────────────────
FRAUD_PATTERNS = [
    # (label, sender_prefix, amount_multiplier, location, hour, tx_type, fraud_reason)
    ("account_takeover",   "STB", 12.0, "Lagos",         2,  "withdrawal",       "account_takeover: off-hours high-value withdrawal from new location"),
    ("account_takeover",   "CEN",  9.5, "Nairobi",       3,  "withdrawal",       "account_takeover: off-hours withdrawal from foreign IP"),
    ("money_laundering",   "CAI", 18.0, "Dubai",         1,  "transfer",         "money_laundering: structuring pattern via high-risk institution"),
    ("money_laundering",   "YKB", 22.0, "London",        23, "transfer",         "money_laundering: late-night large international transfer"),
    ("rapid_succession",   "GTB",  6.0, "Kampala",       3,  "transfer",         "rapid_succession: multiple transfers within minutes"),
    ("rapid_succession",   "GTB",  6.2, "Kampala",       3,  "transfer",         "rapid_succession: multiple transfers within minutes"),
    ("rapid_succession",   "GTB",  5.8, "Kampala",       3,  "transfer",         "rapid_succession: multiple transfers within minutes"),
    ("smurfing",           "YKB",  0.9, "Kampala",       14, "deposit",          "smurfing: repeated just-below-threshold deposits"),
    ("smurfing",           "YKB",  0.9, "Kampala",       14, "deposit",          "smurfing: repeated just-below-threshold deposits"),
    ("smurfing",           "YKB",  0.9, "Entebbe",       15, "deposit",          "smurfing: repeated just-below-threshold deposits"),
    ("smurfing",           "CAI",  0.8, "Jinja",         10, "deposit",          "smurfing: repeated just-below-threshold deposits"),
    ("smurfing",           "CAI",  0.8, "Kampala",       11, "deposit",          "smurfing: repeated just-below-threshold deposits"),
    ("identity_fraud",     "MTN", 30.0, "Dar es Salaam", 4,  "transfer",         "identity_fraud: SIM-swap suspected, device mismatch"),
    ("identity_fraud",     "ATL", 25.0, "Kigali",        4,  "transfer",         "identity_fraud: SIM-swap suspected, device mismatch"),
    ("cross_border",       "SCB", 15.0, "Beijing",       2,  "internal_transfer","cross_border: unusual high-value wire to sanctioned corridor"),
    ("cross_border",       "CTB", 20.0, "Mumbai",        1,  "transfer",         "cross_border: unusual high-value wire to sanctioned corridor"),
    ("ghost_employee",     "BRC",  4.0, "Kampala",       8,  "payment",          "ghost_employee: payroll anomaly, dormant account activated"),
    ("ghost_employee",     "FTB",  4.5, "Kampala",       8,  "payment",          "ghost_employee: payroll anomaly, dormant account activated"),
    ("agent_collusion",    "OPP",  8.0, "Masaka",        22, "withdrawal",       "agent_collusion: agent-side override pattern detected"),
    ("agent_collusion",    "PRB",  7.0, "Mbarara",       22, "withdrawal",       "agent_collusion: agent-side override pattern detected"),
]


def generate_fraud_transactions(days_back: int = 30) -> list[dict]:
    """
    Return a list of synthetic transactions that are explicitly fraudulent.
    Each is crafted to match a real BOU fraud typology.
    Amount is profile_max * amount_multiplier for that institution.
    """
    random.seed(99)
    now = datetime.now(timezone.utc)
    results = []

    for label, prefix, amt_mult, location, hour, tx_type, reason in FRAUD_PATTERNS:
        profile = INSTITUTION_PROFILES.get(prefix, INSTITUTION_PROFILES["GTB"])
        _, max_amt, *_ = profile

        seconds_back = random.randint(3600, days_back * 86400)
        ts = (now - timedelta(seconds=seconds_back)).replace(hour=hour, minute=random.randint(0, 59))

        amount = round(max_amt * amt_mult, 0)
        sender = _random_account(prefix)
        receiver_prefix = _random_receiver_prefix(prefix)
        receiver = _random_account(receiver_prefix, exclude=sender)

        results.append({
            "transaction_id":   f"FRD-{uuid.uuid4().hex[:12].upper()}",
            "sender_account":   sender,
            "receiver_account": receiver,
            "amount":           amount,
            "transaction_type": tx_type,
            "location":         location,
            "device_id":        random.choice(DEVICE_IDS),
            "ip_address":       random.choice(IP_POOL),
            "timestamp":        ts.isoformat(),
            # Pre-labelled — model is not consulted for these
            "_force_fraud":     True,
            "_fraud_reason":    reason,
        })

    return results

def seed_transactions(db_session, n: int = 500) -> dict:
    from app.models.models import Transaction
    from app.models.fraud_model import get_model

    model = get_model()
    now = datetime.now(timezone.utc)
    inserted = 0
    skipped = 0
    fraud_count = 0

    # ── Normal transaction batch (model-scored) ──────────────────────────────
    raw_txns = generate_transactions(n=n)

    # ── Explicit fraud batch (pre-labelled, model bypassed) ──────────────────
    fraud_txns = generate_fraud_transactions()
    all_txns = raw_txns + fraud_txns

    for tx in all_txns:
        exists = db_session.query(Transaction).filter_by(
            transaction_id=tx["transaction_id"]
        ).first()
        if exists:
            skipped += 1
            continue

        force_fraud = tx.pop("_force_fraud", False)
        forced_reason = tx.pop("_fraud_reason", None)

        if force_fraud:
            risk_score  = round(random.uniform(0.75, 0.99), 4)
            is_fraud    = True
            fraud_reason = forced_reason
        else:
            risk_score, is_fraud, fraud_reason = model.score(tx)

        try:
            ts = datetime.fromisoformat(tx["timestamp"].replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            ts = now

        record = Transaction(
            transaction_id=tx["transaction_id"],
            timestamp=ts,
            sender_account=tx["sender_account"],
            receiver_account=tx["receiver_account"],
            amount=tx["amount"],
            transaction_type=tx["transaction_type"],
            location=tx["location"],
            device_id=tx["device_id"],
            ip_address=tx["ip_address"],
            risk_score=round(risk_score, 4),
            is_fraud=is_fraud,
            fraud_reason=fraud_reason,
            model_version="isolation_forest_v1",
            processed_at=now,
        )
        db_session.add(record)
        inserted += 1
        if is_fraud:
            fraud_count += 1

    db_session.commit()

    fraud_rate = round(fraud_count / inserted * 100, 2) if inserted > 0 else 0
    logger.info(
        f"✅ Transaction seed complete: {inserted} inserted "
        f"({len(fraud_txns)} explicit fraud + {n} model-scored), "
        f"{skipped} skipped, {fraud_count} flagged ({fraud_rate}%)"
    )
    return {
        "inserted":       inserted,
        "skipped":        skipped,
        "fraud_flagged":  fraud_count,
        "fraud_rate_pct": fraud_rate,
    }