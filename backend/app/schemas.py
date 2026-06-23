from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class TransactionCreate(BaseModel):
    transaction_id: str
    sender_account: str
    receiver_account: str
    amount: float = Field(gt=0)
    transaction_type: str
    location: Optional[str] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: Optional[str] = None


class TransactionResponse(BaseModel):
    id: str
    transaction_id: str
    timestamp: Optional[str] = None
    sender_account: str
    receiver_account: str
    amount: float
    transaction_type: str
    location: Optional[str] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    risk_score: float
    is_fraud: bool
    fraud_reason: Optional[str] = None
    model_version: str
    processed_at: Optional[str] = None

    class Config:
        from_attributes = True


class HealthCheck(BaseModel):
    status: str
    version: str
    database: str
    redis: str
    model_loaded: bool