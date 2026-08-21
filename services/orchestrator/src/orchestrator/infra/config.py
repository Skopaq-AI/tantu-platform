"""Orchestrator configuration — 12-factor."""

from __future__ import annotations

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "orchestrator"
    env: str = os.getenv("ENV", "development")
    port: int = 8004
    log_level: str = "INFO"

    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://tantu:tantu@localhost:5432/tantu"
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    nats_url: str = os.getenv("NATS_URL", "nats://localhost:4222")
    nats_subjects: str = os.getenv("NATS_SUBJECTS", "tantu.events.derived.>")
    nats_report_subject: str = os.getenv("NATS_REPORT_SUBJECT", "tantu.reports.correlation")

    reasoning_copilot_url: str = os.getenv("REASONING_COPILOT_URL", "http://localhost:8003")
    reasoning_timeout_s: float = float(os.getenv("REASONING_TIMEOUT_S", "8.0"))

    confidence_threshold: float = float(os.getenv("ORCH_CONFIDENCE_THRESHOLD", "0.97"))
    window_size: int = int(os.getenv("ORCH_WINDOW_SIZE", "100"))
    window_ttl_s: float = float(os.getenv("ORCH_WINDOW_TTL_S", "300"))

    downstream_timeout_s: float = 5.0

    @property
    def nats_subjects_list(self) -> list[str]:
        return [s.strip() for s in self.nats_subjects.split(",") if s.strip()]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
