"""
BOU Sentinel — Simulation Router
POST /api/simulate/start   — start background transaction generation
POST /api/simulate/stop    — stop it
GET  /api/simulate/status  — current state

Register in main.py:
  from app.simulate_router import router as simulate_router
  app.include_router(simulate_router)
"""

import asyncio
import json
import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Transaction
from app.models.fraud_model import get_model
from app.compliance_engine import calculate_compliance_risk
from app.seed_institutions import get_institution_from_account
from app.regulatory_models import Institution
from app.ws_manager import manager

logger = logging.getLogger("bou-sentinel.simulate")
router = APIRouter(prefix="/api/simulate", tags=["Simulation"])

# ── Simulation state ──────────────────────────────────────────────────────── #

_task: Optional[asyncio.Task] = None
# Update _stats at the top
_stats = {
    "running":    False,
    "paused":     False,
    "started_at": None,
    "sent":       0,
    "fraud":      0,
    "rate":       1.0,
}

# ── Data tables (mirrors mock_generator.py) ───────────────────────────────── #

PROFILES = {
    "STB": (50_000,    10_000_000, 0.01, 0.05, 0.08),
    "CEN": (30_000,     5_000_000, 0.01, 0.04, 0.07),
    "DFC": (40_000,     8_000_000, 0.01, 0.05, 0.08),
    "ABS": (100_000,   15_000_000, 0.01, 0.06, 0.07),
    "SCB": (500_000,   50_000_000, 0.01, 0.10, 0.06),
    "CTB": (1_000_000, 80_000_000, 0.01, 0.15, 0.06),
    "EQB": (20_000,     3_000_000, 0.02, 0.04, 0.10),
    "KCB": (50_000,    10_000_000, 0.01, 0.05, 0.08),
    "CAI": (50_000,    20_000_000, 0.12, 0.25, 0.20),
    "GTB": (20_000,     3_000_000, 0.06, 0.12, 0.15),
    "YKB": (10_000,     2_000_000, 0.18, 0.35, 0.30),
    "MTN": (1_000,      2_000_000, 0.03, 0.04, 0.12),
    "ATL": (1_000,      1_500_000, 0.03, 0.04, 0.12),
    "OPP": (10_000,     1_000_000, 0.02, 0.04, 0.10),
    "PRB": (10_000,     1_000_000, 0.02, 0.04, 0.10),
    "FIN": (5_000,        500_000, 0.02, 0.03, 0.10),
    "UGA": (5_000,        500_000, 0.02, 0.03, 0.10),
}

ACCOUNTS = {
    "STB": ["STB1000234", "STB2001456", "STB3002789", "STB4003901"],
    "CEN": ["CEN1100234", "CEN2201456", "CEN3302789", "CEN4403901"],
    "DFC": ["DFC1010234", "DFC2020456", "DFC3030789", "DFC4040901"],
    "ABS": ["ABS1001234", "ABS2002456", "ABS3003789", "ABS4004901"],
    "SCB": ["SCB1100001", "SCB2200002", "SCB3300003", "SCB4400004"],
    "CTB": ["CTB1000111", "CTB2000222", "CTB3000333", "CTB4000444"],
    "EQB": ["EQB1001001", "EQB2002002", "EQB3003003", "EQB4004004"],
    "KCB": ["KCB1000001", "KCB2000002", "KCB3000003", "KCB4000004"],
    "CAI": ["CAI1000001", "CAI2000002", "CAI3000003", "CAI4000004"],
    "GTB": ["GTB1000001", "GTB2000002", "GTB3000003", "GTB4000004"],
    "YKB": ["YKB1000001", "YKB2000002", "YKB3000003", "YKB4000004"],
    "MTN": ["MTN2567001", "MTN2567002", "MTN2567003", "MTN7891004"],
    "ATL": ["ATL0701001", "ATL0701002", "ATL0701003", "ATL0312004"],
    "OPP": ["OPP1001001", "OPP2002002", "OPP3003003", "OPP4004004"],
    "PRB": ["PRB1001234", "PRB2002456", "PRB3003789", "PRB4004901"],
    "FIN": ["FIN1001001", "FIN2002002", "FIN3003003", "FIN4004004"],
    "UGA": ["UGA1000001", "UGA2000002", "UGA3000003", "UGA4000004"],
}

DOMESTIC      = ["Kampala","Kampala","Kampala","Entebbe","Jinja","Mbarara","Gulu","Mbale","Lira","Arua"]
INTERNATIONAL = ["Nairobi","Lagos","London","Dubai","Dar es Salaam","Kigali","Johannesburg"]
TX_TYPES      = ["transfer", "deposit", "withdrawal", "payment", "internal_transfer"]
DEVICES       = [f"DEV-{i:06d}" for i in range(1, 101)]
IPS           = [f"41.210.{random.randint(1,254)}.{random.randint(1,254)}" for _ in range(50)]

_prefixes = list(PROFILES)
_weights  = [1 + PROFILES[p][2] * 10 for p in _prefixes]   # fraud-weighted


def _account(prefix: str, exclude: str | None = None) -> str:
    pool = [a for a in ACCOUNTS.get(prefix, [f"{prefix}9999999"]) if a != exclude]
    return random.choice(pool or [f"{prefix}9999999"])


def _make_tx() -> dict:
    prefix = random.choices(_prefixes, weights=_weights)[0]
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

    tx_type = random.choices(
        TX_TYPES,
        weights=[0.35, 0.05, 0.40, 0.15, 0.05] if (is_suspicious or is_off_hours)
                else [0.40, 0.25, 0.20, 0.13, 0.02]
    )[0]

    sender   = _account(prefix)
    rx_pfx   = random.choice(_prefixes) if random.random() > 0.6 else prefix
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


# ── Background task ───────────────────────────────────────────────────────── #

async def _generation_loop(rate: float, db: Session):
    """Async loop: generates and persists one transaction per (1/rate) seconds."""
    model    = get_model()
    interval = 1.0 / rate

    while _stats["running"]:
        tx = _make_tx()

        # Score
        risk_score, is_fraud, fraud_reason = model.score(tx)

        # Parse timestamp
        try:
            ts = datetime.fromisoformat(tx["timestamp"].replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            ts = datetime.now(timezone.utc)

        # Persist
        record = Transaction(
            transaction_id  = tx["transaction_id"],
            timestamp       = ts,
            sender_account  = tx["sender_account"],
            receiver_account= tx["receiver_account"],
            amount          = tx["amount"],
            transaction_type= tx["transaction_type"],
            location        = tx["location"],
            device_id       = tx["device_id"],
            ip_address      = tx["ip_address"],
            risk_score      = round(risk_score, 4),
            is_fraud        = is_fraud,
            fraud_reason    = fraud_reason,
            model_version   = "isolation_forest_v1",
            processed_at    = datetime.now(timezone.utc),
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        _stats["sent"]  += 1
        if is_fraud:
            _stats["fraud"] += 1

        # Broadcast transaction event over WebSocket
        await manager.broadcast(json.dumps({
            "type":            "transaction",
            "id":              record.id,
            "transaction_id":  record.transaction_id,
            "sender_account":  record.sender_account,
            "receiver_account":record.receiver_account,
            "amount":          record.amount,
            "transaction_type":record.transaction_type,
            "location":        record.location,
            "risk_score":      record.risk_score,
            "is_fraud":        record.is_fraud,
            "fraud_reason":    record.fraud_reason,
            "timestamp":       record.timestamp.isoformat(),
            "processed_at":    record.processed_at.isoformat(),
        }))

        # Update institution compliance if sender is a supervised institution
        institution_code = get_institution_from_account(tx["sender_account"])
        if institution_code:
            try:
                inst = db.query(Institution).filter_by(institution_code=institution_code).first()
                if inst:
                    inst.total_transactions = (inst.total_transactions or 0) + 1
                    if is_fraud:
                        inst.fraud_transactions = (inst.fraud_transactions or 0) + 1
                    total = inst.total_transactions
                    inst.fraud_rate = round(
                        (inst.fraud_transactions / total * 100) if total > 0 else 0.0, 4
                    )
                    prev_level = inst.risk_level
                    new_score, new_level, new_issues = calculate_compliance_risk(
                        inst.to_dict(),
                        fraud_stats={
                            "fraud_rate":          inst.fraud_rate,
                            "total_transactions":  inst.total_transactions,
                            "fraud_transactions":  inst.fraud_transactions,
                        },
                    )
                    inst.risk_score = new_score
                    inst.risk_level = new_level
                    inst.set_issues(new_issues)
                    inst.last_risk_updated = datetime.now(timezone.utc)
                    db.add(inst)
                    db.commit()

                    if is_fraud or prev_level != new_level:
                        await manager.broadcast(json.dumps({
                            "type":                "compliance_alert",
                            "institution_code":    inst.institution_code,
                            "institution_name":    inst.name,
                            "tier":                inst.tier,
                            "risk_score":          new_score,
                            "risk_level":          new_level,
                            "previous_risk_level": prev_level,
                            "trigger":             "fraud_detected" if is_fraud else "risk_level_change",
                            "fraud_rate":          inst.fraud_rate,
                            "fraud_transactions":  inst.fraud_transactions,
                            "total_transactions":  inst.total_transactions,
                            "issues":              new_issues[:5],
                            "transaction_id":      tx["transaction_id"],
                            "timestamp":           datetime.now(timezone.utc).isoformat(),
                        }))
            except Exception as e:
                logger.error(f"Compliance update error: {e}")

        await asyncio.sleep(interval)

# Add two new endpoints after /stop:
@router.post("/pause")
async def pause_simulation():
    if not _stats["running"]:
        return {"status": "not_running", **_stats}
    _stats["paused"] = True
    return {"status": "paused", **_stats}


@router.post("/resume")
async def resume_simulation():
    if not _stats["running"]:
        return {"status": "not_running", **_stats}
    _stats["paused"] = False
    return {"status": "running", **_stats}


# Update /stop to also clear paused:
@router.post("/stop")
async def stop_simulation():
    global _task
    if not _stats["running"]:
        return {"status": "not_running", **_stats}
    _stats["running"] = False
    _stats["paused"]  = False
    if _task and not _task.done():
        _task.cancel()
    return {"status": "stopped", **_stats}

logger.info(f"Simulation stopped. Sent {_stats['sent']}, fraud {_stats['fraud']}")


# ── Endpoints ─────────────────────────────────────────────────────────────── #

@router.post("/start")
async def start_simulation(rate: float = 1.0, db: Session = Depends(get_db)):
    """
    Start continuous transaction generation.
    rate — transactions per second (default 1.0, max 10.0)
    """
    global _task

    if _stats["running"]:
        return {"status": "already_running", **_stats}

    rate = max(0.1, min(rate, 10.0))

    _stats.update({
        "running":    True,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "sent":       0,
        "fraud":      0,
        "rate":       rate,
    })

    _task = asyncio.create_task(_generation_loop(rate, db))
    logger.info(f"Simulation started at {rate} tx/s")
    return {"status": "started", **_stats}


@router.get("/status")
async def simulation_status():
    """Current generator state."""
    return _stats