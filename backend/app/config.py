from typing import Optional

from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://bou_user:bou_pass@localhost:5432/bou_sentinel"
    )
    # Redis is optional — only used if installed and configured
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
    REDIS_CHANNEL: str = "fraud_stream"
    APP_NAME: str = "BOU Sentinel - Fraud Detection Engine"
    DEBUG: bool = True

    class Config:
        env_file = ".env"


settings = Settings()