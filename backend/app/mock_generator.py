#!/usr/bin/env python3
"""
BOU Sentinel — Real-Time Transaction Generator
Continuously POSTs synthetic transactions to the running API so the
dashboard feels live.  No app imports — pure HTTP so it works from
any environment that can reach the API.

Usage:
  python mock_generator.py                        # default: ~1 tx/sec
  python mock_generator.py --rate 3               # 3 tx/sec
  python mock_generator.py --rate 0.5             # 1 tx every 2 sec
  python mock_generator.py --rate 2 --burst 5     # bursts of 5 then pause
  python mock_generator.py --duration 60          # run for 60 seconds then stop
  python mock_generator.py --url http://my-vps:8000
"""

import argparse
import json
import random
import time
import uuid
import sys
import signal
from datetime import datetime, timezone, timedelta

# ── Configuration ──────────────────────────────────────────────────────────── #

DEFAULT_URL = "http://localhost:8000"

# Institution profiles: (min_amount, max_amount, fraud_rate, intl_rate, off_hours_rate)
PROFILES = {
    "STB": (50_000,    10_000_000, 0.01, 0.05, 0.08),
    "CEN": (30_000,     5_000_000, 0.01, 0.04, 0.07),
    "DFC": (40_000,     8_000_000, 0.01, 0.05, 0.08),
    "ABS": (100_000,   15_000_000, 0.01, 0.06, 0.07),
    "SCB": (500_000,   50_000_000, 0.01, 0.10, 0.06),
    "CTB": (1_000_000, 80_000_000, 0.01, 0.15, 0.06),
    "EQB": (20_000,     3_000_000, 0.02, 0.04, 0.10),
    "DTB": (50_000,    10_000_000, 0.01, 0.06, 0.08),
    "ECO": (30_000,     5_000_000, 0.02, 0.05, 0.09),
    "KCB": (50_000,    10_000_000, 0.01, 0.05, 0.08),
    "BOA": (40_000,     8_000_000, 0.02, 0.05, 0.09),
    "BRB": (100_000,   20_000_000, 0.01, 0.08, 0.07),
    "BOI": (100_000,   15_000_000, 0.02, 0.07, 0.08),
    "CAI": (50_000,    20_000_000, 0.12, 0.25, 0.20),  # HIGH-RISK
    "EXI": (100_000,   20_000_000, 0.01, 0.07, 0.08),
    "HFB": (50_000,     8_000_000, 0.01, 0.04, 0.08),
    "NCB": (30_000,     5_000_000, 0.01, 0.04, 0.08),
    "IMB": (100_000,   15_000_000, 0.01, 0.06, 0.07),
    "SLM": (30_000,     5_000_000, 0.02, 0.05, 0.09),
    "TRO": (30_000,     5_000_000, 0.02, 0.05, 0.09),
    "UBA": (50_000,    10_000_000, 0.02, 0.06, 0.09),
    "PLB": (30_000,     5_000_000, 0.02, 0.05, 0.10),
    "ABC": (20_000,     3_000_000, 0.02, 0.04, 0.10),
    "GTB": (20_000,     3_000_000, 0.06, 0.12, 0.15),  # MEDIUM-RISK
    "OPP": (10_000,     1_000_000, 0.02, 0.04, 0.10),
    "YKB": (10_000,     2_000_000, 0.18, 0.35, 0.30),  # CRITICAL-RISK
    "BRC": (10_000,     1_000_000, 0.02, 0.04, 0.10),
    "FTB": (10_000,     1_500_000, 0.02, 0.04, 0.10),
    "PRB": (10_000,     1_000_000, 0.02, 0.04, 0.10),
    "FIN": (5_000,        500_000, 0.02, 0.03, 0.10),
    "PRM": (5_000,        500_000, 0.02, 0.03, 0.10),
    "UGA": (5_000,        500_000, 0.02, 0.03, 0.10),
    "MTN": (1_000,      2_000_000, 0.03, 0.04, 0.12),
    "ATL": (1_000,      1_500_000, 0.03, 0.04, 0.12),
}

ACCOUNTS = {
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
    "CAI": ["CAI1000001", "CAI2000002", "CAI3000003", "CAI4000004", "CAI5000005"],
    "EXI": ["EXI1001001", "EXI2002002", "EXI3003003", "EXI4004004", "EXI5005005"],
    "HFB": ["HFB1100234", "HFB2200456", "HFB3300789", "HFB4400901", "HFB5500112"],
    "NCB": ["NCB1001234", "NCB2002456", "NCB3003789", "NCB4004901", "NCB5005112"],
    "IMB": ["IMB1000001", "IMB2000002", "IMB3000003", "IMB4000004", "IMB5000005"],
    "SLM": ["SLM1001234", "SLM2002456", "SLM3003789", "SLM4004901", "SLM5005112"],
    "TRO": ["TRO1000001", "TRO2000002", "TRO3000003", "TRO4000004", "TRO5000005"],
    "UBA": ["UBA1001001", "UBA2002002", "UBA3003003", "UBA4004004", "UBA5005005"],
    "PLB": ["PLB1000234", "PLB2000456", "PLB3000789", "PLB4000901", "PLB5001112"],
    "ABC": ["ABC1001234", "ABC2002456", "ABC3003789", "ABC4004901", "ABC5005112"],
    "GTB": ["GTB1000001", "GTB2000002", "GTB3000003", "GTB4000004", "GTB5000005"],
    "OPP": ["OPP1001001", "OPP2002002", "OPP3003003", "OPP4004004", "OPP5005005"],
    "YKB": ["YKB1000001", "YKB2000002", "YKB3000003", "YKB4000004", "YKB5000005"],
    "BRC": ["BRC1001234", "BRC2002456", "BRC3003789", "BRC4004901", "BRC5005112"],
    "FTB": ["FTB1000001", "FTB2000002", "FTB3000003", "FTB4000004", "FTB5000005"],
    "PRB": ["PRB1001234", "PRB2002456", "PRB3003789", "PRB4004901", "PRB5005112"],
    "FIN": ["FIN1001001", "FIN2002002", "FIN3003003", "FIN4004004", "FIN5005005"],
    "PRM": ["PRM1001234", "PRM2002456", "PRM3003789", "PRM4004901", "PRM5005112"],
    "UGA": ["UGA1000001", "UGA2000002", "UGA3000003", "UGA4000004", "UGA5000005"],
    "MTN": ["MTN2567001", "MTN2567002", "MTN2567003", "MTN7891004", "MTN7891005"],
    "ATL": ["ATL0701001", "ATL0701002", "ATL0701003", "ATL0312004", "ATL0312005"],
}

DOMESTIC = [
    "Kampala", "Kampala", "Kampala",
    "Entebbe", "Jinja", "Mbarara", "Gulu", "Mbale",
    "Kasese", "Fort Portal", "Kabale", "Lira", "Arua",
    "Masaka", "Soroti", "Tororo", "Hoima", "Busia",
]
INTERNATIONAL = [
    "Nairobi", "Lagos", "London", "Dubai", "Dar es Salaam",
    "Kigali", "Johannesburg", "New York", "Beijing", "Mumbai",
]
TX_TYPES = ["transfer", "deposit", "withdrawal", "payment", "internal_transfer"]
DEVICES  = [f"DEV-{i:06d}" for i in range(1, 201)]
IPS = (
    [f"41.210.{random.randint(1,254)}.{random.randint(1,254)}" for _ in range(50)] +
    [f"197.157.{random.randint(1,254)}.{random.randint(1,254)}" for _ in range(30)] +
    [f"41.74.{random.randint(1,254)}.{random.randint(1,254)}" for _ in range(20)]
)


# ── Transaction generation ─────────────────────────────────────────────────── #

def _account(prefix: str, exclude: str | None = None) -> str:
    pool = [a for a in ACCOUNTS.get(prefix, [f"{prefix}9999999"]) if a != exclude]
    return random.choice(pool or ACCOUNTS.get(prefix, [f"{prefix}9999999"]))


def make_transaction(prefix: str | None = None) -> dict:
    prefix = prefix or random.choice(list(PROFILES))
    min_amt, max_amt, fraud_rate, intl_rate, off_hours_rate = PROFILES[prefix]

    now  = datetime.now(timezone.utc)
    hour = now.hour

    is_suspicious = random.random() < fraud_rate
    is_intl       = random.random() < intl_rate
    is_off_hours  = (hour < 6 or hour > 22) or (random.random() < off_hours_rate)

    amount = (
        round(random.uniform(max_amt * 0.8, max_amt * 5), 0) if is_suspicious
        else round(random.uniform(min_amt, max_amt), 0)
    )

    if is_suspicious or is_off_hours:
        tx_type = random.choices(TX_TYPES, weights=[0.35, 0.05, 0.40, 0.15, 0.05])[0]
    else:
        tx_type = random.choices(TX_TYPES, weights=[0.40, 0.25, 0.20, 0.13, 0.02])[0]

    sender   = _account(prefix)
    rx_pfx   = random.choice(list(ACCOUNTS)) if random.random() > 0.6 else prefix
    receiver = _account(rx_pfx, exclude=sender)

    return {
        "transaction_id":   f"TXN-{uuid.uuid4().hex[:12].upper()}",
        "sender_account":   sender,
        "receiver_account": receiver,
        "amount":           amount,
        "transaction_type": tx_type,
        "location":         random.choice(INTERNATIONAL if is_intl else DOMESTIC),
        "device_id":        random.choice(DEVICES),
        "ip_address":       random.choice(IPS),
        "timestamp":        now.isoformat(),
    }


# ── HTTP posting ───────────────────────────────────────────────────────────── #

def post_transaction(tx: dict, base_url: str) -> dict | None:
    """POST a single transaction.  Returns parsed response or None on error."""
    import urllib.request
    import urllib.error

    url     = f"{base_url.rstrip('/')}/api/transactions"
    payload = json.dumps(tx).encode()
    req     = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"  ⚠  HTTP {e.code}: {body[:120]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  ⚠  {e}", file=sys.stderr)
        return None


# ── Runner ─────────────────────────────────────────────────────────────────── #

ANSI = {
    "reset": "\033[0m", "bold": "\033[1m",
    "green": "\033[92m", "red": "\033[91m",
    "yellow": "\033[93m", "cyan": "\033[96m", "grey": "\033[90m",
}

def _color(text: str, *keys: str) -> str:
    return "".join(ANSI[k] for k in keys) + str(text) + ANSI["reset"]


def run(base_url: str, rate: float, burst: int, duration: float | None):
    """
    Main generation loop.

    rate     — average transactions per second
    burst    — how many to send before sleeping
    duration — stop after this many seconds (None = forever)
    """
    interval   = burst / rate           # seconds between bursts
    started_at = time.monotonic()
    total = sent = fraud = errors = 0

    # Weighted prefix list — high-risk institutions appear more often
    # so the dashboard stays interesting
    weights = []
    prefixes = list(PROFILES)
    for p in prefixes:
        _, _, fraud_rate, *_ = PROFILES[p]
        weights.append(1 + fraud_rate * 10)   # high-fraud banks get 2–5× weight

    print(_color(f"\n{'─'*58}", "grey"))
    print(_color(" BOU Sentinel — Real-Time Transaction Generator", "bold", "cyan"))
    print(_color(f" API  : {base_url}", "grey"))
    print(_color(f" Rate : {rate} tx/s  |  Burst : {burst}  |  Interval : {interval:.2f}s", "grey"))
    dur_label = f"{duration}s" if duration else "∞"
    print(_color(f" Duration : {dur_label}", "grey"))
    print(_color(f"{'─'*58}\n", "grey"))

    def _handle_sigint(*_):
        print(_color(f"\n\n Stopped.  Sent {sent} tx  |  {fraud} fraud  |  {errors} errors", "yellow"))
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle_sigint)

    while True:
        if duration and (time.monotonic() - started_at) >= duration:
            break

        batch_start = time.time()

        for _ in range(burst):
            prefix = random.choices(prefixes, weights=weights)[0]
            tx = make_transaction(prefix)
            result = post_transaction(tx, base_url)
            total += 1

            if result:
                sent  += 1
                is_fraud = result.get("is_fraud", False)
                risk     = result.get("risk_score", 0)
                if is_fraud:
                    fraud += 1

                icon  = _color("⚠ FRAUD", "red", "bold") if is_fraud else _color("✓", "green")
                risk_col = "red" if risk > 0.75 else "yellow" if risk > 0.5 else "green"
                risk_str = _color(f"{risk*100:.0f}%", risk_col)

                print(
                    f" {icon}  "
                    f"{_color(result['transaction_id'], 'cyan')}  "
                    f"{_color(tx['sender_account'][:10], 'grey')} → "
                    f"{_color(tx['receiver_account'][:10], 'grey')}  "
                    f"UGX {tx['amount']:>14,.0f}  "
                    f"risk {risk_str}  "
                    f"{_color(tx['location'], 'grey')}"
                )
            else:
                errors += 1
                print(_color(f" ✗ Failed  {tx['transaction_id']}", "red"))

        elapsed = time.time() - batch_start
        sleep   = max(0, interval - elapsed)
        time.sleep(sleep)

    print(_color(f"\n Done.  {sent}/{total} sent  |  {fraud} fraud  |  {errors} errors\n", "green"))


# ── CLI ────────────────────────────────────────────────────────────────────── #

def main():
    parser = argparse.ArgumentParser(
        description="BOU Sentinel real-time transaction generator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--url",      default=DEFAULT_URL, help="API base URL")
    parser.add_argument("--rate",     type=float, default=1.0,  help="Transactions per second")
    parser.add_argument("--burst",    type=int,   default=1,    help="Transactions per burst")
    parser.add_argument("--duration", type=float, default=None, help="Stop after N seconds")
    args = parser.parse_args()

    if args.rate <= 0:
        parser.error("--rate must be > 0")
    if args.burst < 1:
        parser.error("--burst must be >= 1")

    run(
        base_url=args.url,
        rate=args.rate,
        burst=args.burst,
        duration=args.duration,
    )


if __name__ == "__main__":
    main()