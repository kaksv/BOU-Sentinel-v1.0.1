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
from app.models import Transaction
from app.schemas import HealthCheck, TransactionCreate, TransactionResponse
from app.fraud_model import get_model

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bou-sentinel")

# Global Redis connection
redis_client: Optional[aioredis.Redis] = None

# Background tasks
_redis_listener_task: Optional[asyncio.Task] = None


# ============================================================
# WebSocket Connection Manager
# ============================================================
class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts messages to all clients.
    Implements the pub/sub bridge between Redis and connected frontends.
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"🔌 WebSocket client connected. Total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"🔌 WebSocket client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        """Send a message to all connected WebSocket clients."""
        async with self._lock:
            disconnected = []
            for connection in self.active_connections:
                try:
                    await connection.send_text(message)
                except WebSocketDisconnect:
                    disconnected.append(connection)
                except Exception as e:
                    logger.warning(f"⚠️ WebSocket send error: {e}")
                    disconnected.append(connection)

            # Clean up disconnected clients
            for conn in disconnected:
                if conn in self.active_connections:
                    self.active_connections.remove(conn)

    @property
    def count(self) -> int:
        return len(self.active_connections)


manager = ConnectionManager()


# ============================================================
# Redis Pub/Sub Listener (Background Task)
# ============================================================
async def redis_pubsub_listener():
    """
    Background task that subscribes to the Redis fraud_stream channel
    and broadcasts received messages to all connected WebSocket clients.
    """
    global redis_client

    logger.info("📡 Starting Redis Pub/Sub listener...")

    while True:
        try:
            if redis_client is None:
                logger.warning("⏳ Redis not connected. Retrying in 5 seconds...")
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

                    logger.debug(f"📤 Broadcasting to {manager.count} WebSocket client(s)")
                    await manager.broadcast(data)

        except asyncio.CancelledError:
            logger.info("🛑 Redis Pub/Sub listener cancelled.")
            break
        except Exception as e:
            logger.error(f"❌ Redis Pub/Sub error: {e}")
            await asyncio.sleep(5)


# ============================================================
# Application Lifespan
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    global redis_client, _redis_listener_task

    # Startup
    logger.info("🚀 BOU Sentinel starting up...")

    # Initialize database tables
    try:
        init_db()
        logger.info("✅ Database tables initialized")
    except Exception as e:
        logger.warning(f"⚠️ Database initialization skipped: {e}")

    # Connect to Redis
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )
        await redis_client.ping()
        logger.info("✅ Redis connection established")

        # Start the Redis Pub/Sub listener as a background task
        _redis_listener_task = asyncio.create_task(redis_pubsub_listener())
        logger.info("✅ Redis Pub/Sub listener started")
    except Exception as e:
        logger.warning(f"⚠️ Redis connection failed: {e}")
        redis_client = None

    yield

    # Shutdown
    logger.info("🛑 BOU Sentinel shutting down...")

    # Cancel background tasks
    if _redis_listener_task:
        _redis_listener_task.cancel()
        try:
            await _redis_listener_task
        except asyncio.CancelledError:
            pass

    # Close Redis connection
    if redis_client:
        await redis_client.close()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - allow frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# WebSocket Endpoint
# ============================================================
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time transaction streaming.
    Clients connect here to receive live fraud-scored transaction data.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive and handle client messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "stats":
                # Client can request current connection stats
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


# ============================================================
# REST Endpoints
# ============================================================
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - redirect to docs."""
    return {
        "message": "BOU Sentinel - Real-Time Fraud Detection Engine",
        "docs": "/docs",
        "version": "1.0.0",
    }


@app.get("/health", response_model=HealthCheck, tags=["Health"])
async def health_check():
    """Comprehensive health check endpoint."""
    db_status = "disconnected"
    try:
        db = next(get_db())
        db.execute(db.bind.dialect.statement_compiler(db.bind.dialect, db.bind).__class__.__module__)
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
        version="1.0.0",
        database=db_status,
        redis=redis_status,
        model_loaded=model.is_loaded,
    )


@app.get("/api/status", tags=["Status"])
async def api_status():
    """Simple status endpoint for the mock generator."""
    model = get_model()
    return {
        "status": "running",
        "service": "BOU Sentinel",
        "version": "1.0.0",
        "redis_connected": redis_client is not None,
        "model_loaded": model.is_loaded,
        "model_version": "isolation_forest_v1",
        "ws_clients": manager.count,
    }


@app.post("/api/transactions", response_model=TransactionResponse, tags=["Transactions"])
async def create_transaction(
    transaction_data: TransactionCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Receive a transaction, score it with the AI fraud model,
    save it to PostgreSQL, and publish to Redis Pub/Sub channel.
    """
    # Get fraud detection model
    model = get_model()

    # Convert to dict for model scoring
    tx_dict = transaction_data.model_dump()

    # Score the transaction
    risk_score, is_fraud, fraud_reason = model.score(tx_dict)

    # Log the result
    logger.info(
        f"📊 Transaction {transaction_data.transaction_id}: "
        f"risk={risk_score:.2f}, fraud={is_fraud}, reason={fraud_reason}"
    )

    # Parse timestamp if provided
    timestamp = None
    if transaction_data.timestamp:
        try:
            timestamp = datetime.fromisoformat(
                transaction_data.timestamp.replace("Z", "+00:00")
            )
        except (ValueError, AttributeError):
            timestamp = datetime.now(timezone.utc)

    # Create database record
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

    # Build response
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

    # Publish to Redis channel - the Pub/Sub listener will broadcast via WebSocket
    if redis_client:
        try:
            await redis_client.publish(
                settings.REDIS_CHANNEL,
                response.model_dump_json(),
            )
            logger.debug(f"📤 Published transaction to Redis channel: {settings.REDIS_CHANNEL}")
        except Exception as e:
            logger.error(f"Failed to publish to Redis: {e}")

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
    """Get aggregate statistics for the dashboard."""
    total = db.query(Transaction).count()
    fraud_count = db.query(Transaction).filter(Transaction.is_fraud == True).count()
    avg_risk = db.query(Transaction).with_entities(
        db.query(Transaction.risk_score).subquery().c.risk_score
    ).all()

    # Get recent transaction counts by minute for the chart
    recent_txs = (
        db.query(
            func.date_trunc('minute', Transaction.processed_at).label('minute'),
            func.count().label('total'),
            func.sum(case((Transaction.is_fraud == True, 1), else_=0)).label('fraud')
        )
        .group_by(func.date_trunc('minute', Transaction.processed_at))
        .order_by(func.date_trunc('minute', Transaction.processed_at).desc())
        .limit(30)
        .all()
    )

    return {
        "total_transactions": total,
        "fraud_transactions": fraud_count,
        "fraud_rate": round(fraud_count / total * 100, 2) if total > 0 else 0,
        "avg_risk_score": round(
            sum(r[0] for r in avg_risk if r[0]) / len(avg_risk), 4
        ) if avg_risk else 0,
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