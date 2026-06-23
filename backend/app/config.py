from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://bou_user:bou_pass@localhost:5432/bou_sentinel"
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_CHANNEL: str = "fraud_stream"
    APP_NAME: str = "BOU Sentinel - Fraud Detection Engine"
    DEBUG: bool = True

    class Config:
        env_file = ".env"


settings = Settings()