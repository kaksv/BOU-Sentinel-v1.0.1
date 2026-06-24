#!/usr/bin/env python3
"""
BOU Sentinel - Mock Data Generator
Generates realistic Ugandan banking transactions and POSTs them to the FastAPI backend.
Includes a "Fraud Spike" trigger for hackathon demos.

Usage:
    python mock_generator.py                    # Normal mode (1 tx/sec)
    python mock_generator.py --spike            # Fraud spike mode
    python mock_generator.py --rate 5           # Custom rate (tx/sec)
    python mock_generator.py --api http://localhost:8000
"""

import argparse
import json
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests

# ============================================================
# Configuration
# ============================================================
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_RATE = 1  # transactions per second

# Ugandan names for realistic data
FIRST_NAMES = [
    "Moses", "Grace", "John", "Sarah", "David", "Esther", "Samuel", "Ruth",
    "Daniel", "Mary", "Joseph", "Rebecca", "Peter", "Jane", "Paul", "Joy",
    "James", "Rose", "Andrew", "Catherine", "Simon", "Alice", "Robert", "Margaret",
    "Charles", "Agnes", "William", "Dorothy", "George", "Faith", "Henry", "Peace",
    "Patrick", "Phiona", "Edward", "Patience", "Michael", "Jacqueline", "Isaac",
    "Martha", "Fred", "Juliet", "Brian", "Diana", "Ronald", "Vicky", "Kenneth", "Eva",
]

LAST_NAMES = [
    "Mugisha", "Nanyonjo", "Ochen", "Nakato", "Kato", "Babirye", "Ssali", "Nantongo",
    "Okello", "Mutesi", "Wasswa", "Nabatanzi", "Kizza", "Nalwanga", "Musisi", "Nakamya",
    "Lubega", "Nalule", "Mukasa", "Nakitende", "Kintu", "Nakitto", "Kizito", "Nambi",
    "Ssebbowa", "Namukasa", "Muwonge", "Namatovu", "Kasule", "Nakalema",
    "Akiiki", "Nabasumba", "Baguma", "Nantamu", "Baluku", "Kiconco", "Masereka", "Mbabazi",
    "Tumusiime", "Niwebyona", "Busingye", "Nyiramahoro", "Hakiza", "Muhindo", "Kyomugisha",
]

LOCATIONS = [
    "Kampala", "Entebbe", "Jinja", "Mbarara", "Gulu", "Mbale",
    "Masaka", "Lira", "Fort Portal", "Arua", "Soroti", "Kabale",
    "Busia", "Tororo", "Hoima", "Iganga", "Mukono", "Kasese",
]

INTERNATIONAL_LOCATIONS = [
    "Nairobi", "Lagos", "London", "Dubai", "New York",
    "Johannesburg", "Beijing", "Mumbai", "Istanbul", "Frankfurt",
]

ACCOUNT_PREFIXES = ["01", "10", "20", "30", "40", "50", "60", "70", "80", "90"]
BANK_CODES = ["BOFU", "STAN", "ABCL", "BARL", "CITI", "DFCU", "EQTY", "KCB", "NICO", "POST"]


def generate_account_number() -> str:
    """Generate a realistic Ugandan bank account number (10-14 digits)."""
    prefix = random.choice(ACCOUNT_PREFIXES)
    suffix = "".join([str(random.randint(0, 9)) for _ in range(8)])
    return f"{prefix}{suffix}"


def generate_transaction(
    is_fraud: bool = False,
    fraud_intensity: float = 1.0,
) -> Dict:
    """
    Generate a single realistic transaction.

    Args:
        is_fraud: Force this to be a fraudulent transaction
        fraud_intensity: 0.0-1.0, how extreme the fraud indicators are

    Returns:
        Transaction dict ready to POST
    """
    tx_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
    timestamp = datetime.now(timezone.utc).isoformat()

    # Generate random sender/receiver names
    sender_first = random.choice(FIRST_NAMES)
    sender_last = random.choice(LAST_NAMES)
    receiver_first = random.choice(FIRST_NAMES)
    receiver_last = random.choice(LAST_NAMES)

    sender_account = generate_account_number()
    receiver_account = generate_account_number()

    # Determine transaction type
    if is_fraud:
        tx_types = ["transfer", "withdrawal"]  # Fraud tends to be transfers/withdrawals
    else:
        tx_types = ["transfer", "deposit", "withdrawal", "payment", "internal_transfer"]
    tx_type = random.choice(tx_types)

    # Generate amount (in UGX)
    if is_fraud:
        # Fraud amounts: large, suspicious
        if fraud_intensity > 0.8:
            amount = round(random.uniform(15_000_000, 100_000_000), 2)  # 15M-100M
        elif fraud_intensity > 0.5:
            amount = round(random.uniform(8_000_000, 25_000_000), 2)  # 8M-25M
        else:
            amount = round(random.uniform(5_000_000, 15_000_000), 2)  # 5M-15M
    else:
        # Normal amounts: 10k - 5M
        amount = round(random.lognormvariate(12.5, 1.5), 2)

    # Location
    if is_fraud and random.random() < 0.7:
        location = random.choice(INTERNATIONAL_LOCATIONS)
    else:
        location = random.choice(LOCATIONS)

    # Device and IP
    device_id = f"DEV-{uuid.uuid4().hex[:8].upper()}" if random.random() < 0.7 else None
    ip_address = f"{random.randint(10, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

    transaction = {
        "transaction_id": tx_id,
        "sender_account": sender_account,
        "receiver_account": receiver_account,
        "amount": amount,
        "transaction_type": tx_type,
        "location": location,
        "device_id": device_id,
        "ip_address": ip_address,
        "timestamp": timestamp,
    }

    return transaction


def post_transaction(api_url: str, transaction: Dict) -> Optional[Dict]:
    """POST a transaction to the FastAPI backend and return the response."""
    url = f"{api_url}/api/transactions"
    try:
        response = requests.post(url, json=transaction, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Failed to POST: {e}", file=sys.stderr)
        return None


def print_transaction(tx: Dict, result: Optional[Dict]):
    """Pretty-print a transaction and its fraud score."""
    if result:
        risk = result.get("risk_score", 0)
        is_fraud = result.get("is_fraud", False)
        reason = result.get("fraud_reason", "")

        risk_bar = "█" * int(risk * 20) + "░" * (20 - int(risk * 20))
        fraud_flag = "🔴 FRAUD" if is_fraud else "🟢 CLEAN"

        print(f"  {fraud_flag} | {tx['transaction_id']}")
        print(f"    Amount: UGX {tx['amount']:>12,.2f} | Type: {tx['transaction_type']:>15} | Location: {tx['location']:>15}")
        print(f"    Risk:   {risk_bar} {risk:.2%}")
        if reason:
            print(f"    Reason: {reason}")
    else:
        print(f"  ⚪ {tx['transaction_id']} - No response")


# ============================================================
# Fraud Spike Generator
# ============================================================
def generate_fraud_spike(api_url: str, num_transactions: int = 50):
    """
    Generate a burst of high-risk fraudulent transactions for the hackathon demo.
    Simulates a coordinated fraud attack.

    Args:
        api_url: Backend API URL
        num_transactions: Number of fraud transactions to generate (default: 50)
    """
    print(f"\n{'='*70}")
    print(f"  🚨 FRAUD SPIKE TRIGGERED! Generating {num_transactions} fraudulent transactions...")
    print(f"{'='*70}\n")

    # Use a single compromised account for the attack
    compromised_account = generate_account_number()
    attacker_device = f"DEV-HACK-{uuid.uuid4().hex[:6].upper()}"
    attacker_ip = f"{random.randint(100, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

    successful = 0
    start_time = time.time()

    for i in range(num_transactions):
        # Generate high-intensity fraud transactions
        tx = generate_transaction(is_fraud=True, fraud_intensity=1.0)

        # Override with coordinated attack pattern
        if i % 3 == 0:
            tx["sender_account"] = compromised_account  # Same source account
        if i % 5 == 0:
            tx["device_id"] = attacker_device  # Same device
        if i % 7 == 0:
            tx["ip_address"] = attacker_ip  # Same IP

        # Vary amounts for realism
        tx["amount"] = round(random.uniform(20_000_000, 80_000_000), 2)

        # Some to known international fraud hotspots
        if i < num_transactions // 3:
            tx["location"] = "Lagos"
        elif i < 2 * num_transactions // 3:
            tx["location"] = "Nairobi"

        print(f"  [{i+1}/{num_transactions}] POSTing {tx['transaction_id']}...")
        result = post_transaction(api_url, tx)
        if result:
            successful += 1
            risk = result.get("risk_score", 0)
            flag = "🔴" if result.get("is_fraud") else "⚠️"
            print(f"    {flag} Risk: {risk:.2%} | {result.get('fraud_reason', 'No reason')}")

        # Burst: send 2-3 per second with no delay at start
        if i < 10:
            time.sleep(0.1)  # Very fast for first 10
        elif i < 30:
            time.sleep(0.3)  # Fast for next 20
        else:
            time.sleep(0.5)  # Normal pace for rest

    elapsed = time.time() - start_time
    print(f"\n{'='*70}")
    print(f"  ✅ Fraud spike complete!")
    print(f"  📊 {successful}/{num_transactions} transactions posted successfully")
    print(f"  ⏱️  Duration: {elapsed:.1f}s ({num_transactions/elapsed:.1f} tx/s)")
    print(f"{'='*70}\n")


# ============================================================
# Normal Mode - Continuous Generation
# ============================================================
def run_continuous(api_url: str, rate: float = DEFAULT_RATE):
    """Continuously generate and post transactions at the given rate."""
    print(f"\n{'='*70}")
    print(f"  📊 BOU Sentinel - Mock Data Generator")
    print(f"  🌐 API: {api_url}")
    print(f"  ⚡ Rate: {rate} tx/s")
    print(f"  🕒 Started: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*70}\n")

    # Check API health
    try:
        health = requests.get(f"{api_url}/health", timeout=3)
        print(f"  ✅ API Health: {health.json().get('status', 'unknown')}")
        print(f"  🧠 Model: {'Loaded' if health.json().get('model_loaded') else 'Not loaded'}")
    except Exception as e:
        print(f"  ⚠️  Could not reach API: {e}")
        print(f"  Will retry on each POST...\n")

    stats = {"total": 0, "fraud": 0, "errors": 0}
    fraud_chance = 0.05  # 5% of transactions are fraud by default
    next_fraud_spike = random.randint(50, 150)  # Trigger spike after N transactions

    try:
        while True:
            # Check if we should trigger a fraud spike
            stats["total"] += 1
            if stats["total"] >= next_fraud_spike:
                generate_fraud_spike(api_url, num_transactions=50)
                next_fraud_spike = stats["total"] + random.randint(100, 200)
                fraud_chance = 0.05  # Reset to normal
                continue

            # Generate normal traffic
            is_fraud_tx = random.random() < fraud_chance
            tx = generate_transaction(is_fraud=is_fraud_tx, fraud_intensity=random.uniform(0.3, 0.9))

            # Print status line
            print(f"\r  [{datetime.now().strftime('%H:%M:%S')}] TX #{stats['total']} | "
                  f"{'🔴' if is_fraud_tx else '🟢'} UGX {tx['amount']:>12,.2f} | "
                  f"{tx['location']:>15} | {tx['transaction_type']:>15}    ",
                  end="", flush=True)

            result = post_transaction(api_url, tx)
            if result:
                if result.get("is_fraud"):
                    stats["fraud"] += 1
                if stats["total"] % 10 == 0:
                    print(f"\n  📈 Stats: {stats['total']} txns | "
                          f"{stats['fraud']} fraud ({stats['fraud']/stats['total']*100:.1f}%) | "
                          f"{stats['errors']} errors")
            else:
                stats["errors"] += 1

            # Wait for next transaction
            time.sleep(1.0 / rate)

    except KeyboardInterrupt:
        elapsed = time.time() - start_time if 'start_time' in dir() else 0
        print(f"\n\n{'='*70}")
        print(f"  📊 Generation stopped by user")
        print(f"  📈 Total: {stats['total']} | Fraud: {stats['fraud']} | Errors: {stats['errors']}")
        print(f"{'='*70}\n")


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="BOU Sentinel - Mock Transaction Data Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python mock_generator.py                          # Normal: 1 tx/sec
  python mock_generator.py --spike                   # Fraud spike (50 transactions)
  python mock_generator.py --spike --count 100       # Custom spike (100 transactions)
  python mock_generator.py --rate 5                  # 5 transactions/sec
  python mock_generator.py --api http://localhost:8000  # Custom API URL
        """,
    )

    parser.add_argument(
        "--api",
        default=DEFAULT_API_URL,
        help=f"Backend API URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=DEFAULT_RATE,
        help=f"Transactions per second in continuous mode (default: {DEFAULT_RATE})",
    )
    parser.add_argument(
        "--spike",
        action="store_true",
        help="Run a single fraud spike and exit",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=50,
        help="Number of transactions for fraud spike (default: 50)",
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="Generate and POST a single transaction, then exit",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed the institution database with BOU-regulated institutions",
    )

    args = parser.parse_args()

    # Ensure API URL has no trailing slash
    api_url = args.api.rstrip("/")

    if args.seed:
        # Seed institution database
        print(f"\nSeeding institution database...")
        try:
            res = requests.post(f"{api_url}/api/institutions/seed", timeout=30)
            if res.status_code == 200:
                data = res.json()
                print(f"✅ {data.get('message', 'Done')}")
                print(json.dumps(data, indent=2))
            else:
                print(f"❌ Seed failed: {res.status_code} {res.text}")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Seed error: {e}")
            sys.exit(1)

    elif args.single:
        # Single transaction mode
        tx = generate_transaction()
        print(f"\nGenerating single transaction...")
        print(json.dumps(tx, indent=2))
        result = post_transaction(api_url, tx)
        if result:
            print(f"\nResult:")
            print(json.dumps(result, indent=2))
        else:
            sys.exit(1)

    elif args.spike:
        # Fraud spike mode
        generate_fraud_spike(api_url, args.count)

    else:
        # Continuous mode
        run_continuous(api_url, args.rate)


if __name__ == "__main__":
    main()