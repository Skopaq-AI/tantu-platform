"""Adapter-fabric configuration — 12-factor, Pydantic Settings."""

from __future__ import annotations

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "adapter-fabric"
    env: str = os.getenv("ENV", "development")
    port: int = 8001
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://tantu:tantu@localhost:5432/tantu"
    )
    nats_url: str = os.getenv("NATS_URL", "nats://localhost:4222")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
