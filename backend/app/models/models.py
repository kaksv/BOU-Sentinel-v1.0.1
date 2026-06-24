import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Boolean, DateTime, Integer, Text
from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = Column(String, unique=True, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    sender_account = Column(String, nullable=False)
    receiver_account = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String, nullable=False)  # e.g. transfer, deposit, withdrawal
    location = Column(String, nullable=True)
    device_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)

    # Fraud detection fields
    risk_score = Column(Float, default=0.0)
    is_fraud = Column(Boolean, default=False)
    fraud_reason = Column(String, nullable=True)

    # Model metadata
    model_version = Column(String, default="isolation_forest_v1")
    processed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "transaction_id": self.transaction_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "sender_account": self.sender_account,
            "receiver_account": self.receiver_account,
            "amount": self.amount,
            "transaction_type": self.transaction_type,
            "location": self.location,
            "device_id": self.device_id,
            "ip_address": self.ip_address,
            "risk_score": self.risk_score,
            "is_fraud": self.is_fraud,
            "fraud_reason": self.fraud_reason,
            "model_version": self.model_version,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }