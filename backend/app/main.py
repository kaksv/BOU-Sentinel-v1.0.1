"""
BOU Sentinel - Main Application
Real-time fraud detection + regulatory compliance monitoring for Bank of Uganda.

Changes from base version:
  - ConnectionManager moved to app.ws_manager (singleton)
  - Regulatory compliance router registered at /api/regulatory
  - Institutions seeded on startup from seed_institutions.py
  - create_transaction() now links transactions to supervised institutions
    and re-scores their compliance risk in real-time via the compliance engine
  - Compliance alerts are broadcast over the same /ws WebSocket channel;
    frontends filter by message type: "transaction" | "compliance_alert"
"""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional

import redis.asyncio as aioredis
from fastapi import FastAPI, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.config import settings
from app.database import init_db, get_db

# ── Fraud detection ──────────────────────────────────────────────────────────
from app.models.models import Transaction
from app.schemas import HealthCheck, TransactionCreate, TransactionResponse
from app.fraud_model import get_model
from app.institution_router import router as institution_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bou-sentinel")

redis_client: Optional[aioredis.Redis] = None
_redis_listener_task: Optional[asyncio.Task] = None


# ─────────────────────────────────────────────────────────────────────────────
# REDIS PUB/SUB LISTENER
# ─────────────────────────────────────────────────────────────────────────────

async def redis_pubsub_listener():
    """
    Background task — subscribes to the Redis fraud_stream channel
    and broadcasts received messages to all connected WebSocket clients.
    """
    global redis_client
    logger.info("📡 Starting Redis Pub/Sub listener...")

    while True:
        try:
            if redis_client is None:
                await asyncio.sleep(5)
                continue

            pubsub = redis_client.pubsub()
            await pubsub.subscribe(settings.REDIS_CHANNEL)
            logger.info(f"✅ Subscribed to Redis channel: {settings.REDIS_CHANNEL}")

            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    await manager.broadcast(data)

        except asyncio.CancelledError:
            logger.info("🛑 Redis Pub/Sub listener cancelled.")
            break
        except Exception as e:
            logger.error(f"❌ Redis Pub/Sub error: {e}")
            await asyncio.sleep(5)


# ─────────────────────────────────────────────────────────────────────────────
# APPLICATION LIFESPAN
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, _redis_listener_task

    logger.info("🚀 BOU Sentinel starting up...")

    # 1. Initialise database tables (Transaction + Institution + ComplianceReport)
    try:
        init_db()
        logger.info("✅ Database tables initialised")
    except Exception as e:
        logger.warning(f"⚠️  Database init skipped: {e}")

    # 2. Seed BOU-supervised institutions
    try:
        db = next(get_db())
        count = seed_institutions(db)
        if count:
            logger.info(f"✅ Seeded {count} BOU-supervised institutions")
        else:
            logger.info("ℹ️  Institution seed: all records already present")
        db.close()
    except Exception as e:
        logger.warning(f"⚠️  Institution seed failed: {e}")

    # 3. Connect to Redis
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("✅ Redis connection established")
        _redis_listener_task = asyncio.create_task(redis_pubsub_listener())
        logger.info("✅ Redis Pub/Sub listener started")
    except Exception as e:
        logger.warning(f"⚠️  Redis unavailable: {e}")
        redis_client = None

    yield

    # Shutdown
    logger.info("🛑 BOU Sentinel shutting down...")
    if _redis_listener_task:
        _redis_listener_task.cancel()
        try:
            await _redis_listener_task
        except asyncio.CancelledError:
            pass
    if redis_client:
        await redis_client.close()


# ─────────────────────────────────────────────────────────────────────────────
# APP FACTORY
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include institutional monitoring routes
app.include_router(institution_router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Real-time stream.  Clients receive two event types:
      {"type": "transaction",      ...fraud-scored transaction data...}
      {"type": "compliance_alert", ...institution risk change...}
    Filter on the client by `data.type`.
    """
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "stats":
                await websocket.send_text(json.dumps({
                    "type": "ws_stats",
                    "connected_clients": manager.count,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }))
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        await manager.disconnect(websocket)


# ─────────────────────────────────────────────────────────────────────────────
# ROOT / HEALTH / STATUS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "BOU Sentinel — Real-Time Fraud Detection & Regulatory Compliance Engine",
        "docs": "/docs",
        "version": "2.0.0",
        "features": ["fraud_detection", "regulatory_compliance", "real_time_ws"],
    }


@app.get("/health", response_model=HealthCheck, tags=["Health"])
async def health_check():
    db_status = "disconnected"
    try:
        db = next(get_db())
        db.execute(db.bind.dialect.statement_compiler(
            db.bind.dialect, db.bind).__class__.__module__)
        db.close()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    redis_status = "disconnected"
    if redis_client:
        try:
            await redis_client.ping()
            redis_status = "connected"
        except Exception:
            redis_status = "disconnected"

    model = get_model()
    return HealthCheck(
        status="healthy",
        version="2.0.0",
        database=db_status,
        redis=redis_status,
        model_loaded=model.is_loaded,
    )


@app.get("/api/status", tags=["Status"])
async def api_status():
    model = get_model()
    return {
        "status": "running",
        "service": "BOU Sentinel",
        "version": "2.0.0",
        "redis_connected": redis_client is not None,
        "model_loaded": model.is_loaded,
        "model_version": "isolation_forest_v1",
        "ws_clients": manager.count,
        "features": ["fraud_detection", "regulatory_compliance"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# TRANSACTION ENDPOINTS  (original + institution linkage)
# ─────────────────────────────────────────────────────────────────────────────

def _update_institution_fraud_stats(
    institution_code: str,
    is_fraud: bool,
    db: Session,
) -> Optional[Institution]:
    """
    Atomically increment an institution's transaction counters
    and recompute its fraud_rate.  Returns the updated Institution or None.
    """
    inst = db.query(Institution).filter_by(institution_code=institution_code).first()
    if not inst:
        return None

    inst.total_transactions = (inst.total_transactions or 0) + 1
    if is_fraud:
        inst.fraud_transactions = (inst.fraud_transactions or 0) + 1

    total = inst.total_transactions
    inst.fraud_rate = round(
        (inst.fraud_transactions / total * 100) if total > 0 else 0.0, 4
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


@app.post("/api/transactions", response_model=TransactionResponse, tags=["Transactions"])
async def create_transaction(
    transaction_data: TransactionCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Receive a transaction, score it with the AI fraud model,
    persist to PostgreSQL, publish to Redis Pub/Sub, and —
    NEW — link the transaction to the sender's supervised institution,
    updating that institution's fraud stats and re-scoring its
    regulatory compliance risk in real-time.
    """
    model = get_model()
    tx_dict = transaction_data.model_dump()

    # ── Fraud scoring ────────────────────────────────────────────────────────
    risk_score, is_fraud, fraud_reason = model.score(tx_dict)
    logger.info(
        f"📊 Transaction {transaction_data.transaction_id}: "
        f"risk={risk_score:.2f}, fraud={is_fraud}, reason={fraud_reason}"
    )

    # ── Parse timestamp ──────────────────────────────────────────────────────
    timestamp = None
    if transaction_data.timestamp:
        try:
            timestamp = datetime.fromisoformat(
                transaction_data.timestamp.replace("Z", "+00:00")
            )
        except (ValueError, AttributeError):
            timestamp = datetime.now(timezone.utc)

    # ── Persist transaction ──────────────────────────────────────────────────
    db_transaction = Transaction(
        transaction_id=transaction_data.transaction_id,
        timestamp=timestamp or datetime.now(timezone.utc),
        sender_account=transaction_data.sender_account,
        receiver_account=transaction_data.receiver_account,
        amount=transaction_data.amount,
        transaction_type=transaction_data.transaction_type,
        location=transaction_data.location,
        device_id=transaction_data.device_id,
        ip_address=transaction_data.ip_address,
        risk_score=round(risk_score, 4),
        is_fraud=is_fraud,
        fraud_reason=fraud_reason,
        model_version="isolation_forest_v1",
        processed_at=datetime.now(timezone.utc),
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    # ── Build API response ───────────────────────────────────────────────────
    response = TransactionResponse(
        id=db_transaction.id,
        transaction_id=db_transaction.transaction_id,
        timestamp=db_transaction.timestamp.isoformat() if db_transaction.timestamp else None,
        sender_account=db_transaction.sender_account,
        receiver_account=db_transaction.receiver_account,
        amount=db_transaction.amount,
        transaction_type=db_transaction.transaction_type,
        location=db_transaction.location,
        device_id=db_transaction.device_id,
        ip_address=db_transaction.ip_address,
        risk_score=db_transaction.risk_score,
        is_fraud=db_transaction.is_fraud,
        fraud_reason=db_transaction.fraud_reason,
        model_version=db_transaction.model_version,
        processed_at=db_transaction.processed_at.isoformat() if db_transaction.processed_at else None,
    )

    # ── Publish transaction event to Redis → WebSocket ────────────────────────
    tx_event = {**response.model_dump(), "type": "transaction"}
    if redis_client:
        try:
            await redis_client.publish(settings.REDIS_CHANNEL, json.dumps(tx_event))
        except Exception as e:
            logger.error(f"Failed to publish transaction to Redis: {e}")

    # ── [NEW] Link transaction to institution & re-score compliance ────────────
    institution_code = get_institution_from_account(transaction_data.sender_account)
    if institution_code:
        try:
            inst = _update_institution_fraud_stats(institution_code, is_fraud, db)
            if inst:
                previous_level = inst.risk_level

                # Re-run compliance engine with updated fraud stats
                new_score, new_level, new_issues = calculate_compliance_risk(
                    inst.to_dict(),
                    fraud_stats={
                        "fraud_rate": inst.fraud_rate,
                        "total_transactions": inst.total_transactions,
                        "fraud_transactions": inst.fraud_transactions,
                    },
                )

                inst.risk_score = new_score
                inst.risk_level = new_level
                inst.set_issues(new_issues)
                inst.last_risk_updated = datetime.now(timezone.utc)
                db.add(inst)
                db.commit()

                # Broadcast compliance alert if fraud detected OR risk level changed
                if is_fraud or previous_level != new_level:
                    alert = {
                        "type": "compliance_alert",
                        "institution_code": inst.institution_code,
                        "institution_name": inst.name,
                        "tier": inst.tier,
                        "risk_score": new_score,
                        "risk_level": new_level,
                        "previous_risk_level": previous_level,
                        "trigger": "fraud_detected" if is_fraud else "risk_level_change",
                        "fraud_rate": inst.fraud_rate,
                        "fraud_transactions": inst.fraud_transactions,
                        "total_transactions": inst.total_transactions,
                        "issues": new_issues[:5],
                        "transaction_id": transaction_data.transaction_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    await manager.broadcast(json.dumps(alert))
                    logger.info(
                        f"🏦 Compliance alert: {inst.institution_code} "
                        f"fraud_rate={inst.fraud_rate:.1f}% | "
                        f"risk: {previous_level} → {new_level}"
                    )
        except Exception as e:
            logger.error(f"❌ Institution compliance update failed: {e}")
            # Non-fatal — transaction was already saved successfully

    return response


@app.get("/api/transactions", tags=["Transactions"])
async def get_transactions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Get recent transactions from the database."""
    transactions = (
        db.query(Transaction)
        .order_by(Transaction.processed_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [tx.to_dict() for tx in transactions]


@app.get("/api/transactions/fraud", tags=["Transactions"])
async def get_fraud_transactions(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Get flagged fraudulent transactions."""
    transactions = (
        db.query(Transaction)
        .filter(Transaction.is_fraud == True)
        .order_by(Transaction.processed_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [tx.to_dict() for tx in transactions]


@app.get("/api/stats", tags=["Statistics"])
async def get_stats(db: Session = Depends(get_db)):
    """Aggregate statistics for the fraud detection dashboard."""
    total = db.query(Transaction).count()
    fraud_count = db.query(Transaction).filter(Transaction.is_fraud == True).count()

    avg_risk_rows = db.query(Transaction.risk_score).all()
    avg_risk = (
        round(sum(r[0] for r in avg_risk_rows if r[0]) / len(avg_risk_rows), 4)
        if avg_risk_rows else 0
    )

    recent_txs = (
        db.query(
            func.date_trunc("minute", Transaction.processed_at).label("minute"),
            func.count().label("total"),
            func.sum(case((Transaction.is_fraud == True, 1), else_=0)).label("fraud"),
        )
        .group_by(func.date_trunc("minute", Transaction.processed_at))
        .order_by(func.date_trunc("minute", Transaction.processed_at).desc())
        .limit(30)
        .all()
    )

    return {
        "total_transactions": total,
        "fraud_transactions": fraud_count,
        "fraud_rate": round(fraud_count / total * 100, 2) if total > 0 else 0,
        "avg_risk_score": avg_risk,
        "recent_activity": [
            {
                "minute": row.minute.isoformat() if row.minute else None,
                "total": row.total,
                "fraud": row.fraud or 0,
            }
            for row in recent_txs
        ],
        "ws_connected_clients": manager.count,
    }