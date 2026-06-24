import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from fastapi import FastAPI, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.config import settings
from app.database import init_db, get_db
from app.models import Transaction
from app.schemas import HealthCheck, TransactionCreate, TransactionResponse
from app.fraud_model import get_model
from app.institution_router import router as institution_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bou-sentinel")

# Redis is optional — WebSocket broadcasts work directly without it
redis_client = None


# ============================================================
# WebSocket Connection Manager
# ============================================================
class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts messages to all clients.
    This is the core real-time streaming mechanism — works without Redis.
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

            for conn in disconnected:
                if conn in self.active_connections:
                    self.active_connections.remove(conn)

    @property
    def count(self) -> int:
        return len(self.active_connections)


manager = ConnectionManager()


# ============================================================
# Application Lifespan
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    global redis_client

    # Startup
    logger.info("🚀 BOU Sentinel starting up...")

    # Initialize database tables
    try:
        init_db()
        logger.info("✅ Database tables initialized")
    except Exception as e:
        logger.warning(f"⚠️ Database initialization skipped: {e}")

    # Connect to Redis (optional — only if URL and package are available)
    if REDIS_AVAILABLE:
        try:
            redis_client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True
            )
            await redis_client.ping()
            logger.info("✅ Redis connection established")
        except Exception as e:
            logger.info(f"ℹ️ Redis not available — WebSocket broadcasts work without it. ({e})")
            redis_client = None
    else:
        logger.info("ℹ️ Redis not installed — WebSocket broadcasts work without it.")

    yield

    # Shutdown
    logger.info("🛑 BOU Sentinel shutting down...")
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

# Include institutional monitoring routes
app.include_router(institution_router)


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

    redis_status = "not_configured"
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
    save it to PostgreSQL, and broadcast to WebSocket clients.
    """
    model = get_model()
    tx_dict = transaction_data.model_dump()

    # Score with AI model
    risk_score, is_fraud, fraud_reason = model.score(tx_dict)

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

    response_json = response.model_dump_json()

    # Broadcast to all WebSocket clients directly (no Redis needed!)
    await manager.broadcast(response_json)

    # Also publish to Redis if available (for scaling to multiple instances)
    if redis_client:
        try:
            await redis_client.publish(settings.REDIS_CHANNEL, response_json)
        except Exception as e:
            logger.debug(f"Redis publish skipped: {e}")

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