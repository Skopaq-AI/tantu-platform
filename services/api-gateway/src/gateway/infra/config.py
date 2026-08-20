"""Gateway configuration — 12-factor, Pydantic Settings."""
from __future__ import annotations

import os
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


def _cors_origins(v: str | list[str]) -> list[str]:
    if isinstance(v, list):
        return v
    if v.strip() == "*":
        return ["*"]
    return [o.strip() for o in v.split(",") if o.strip()]


class Settings(BaseSettings):
    service_name: str = "api-gateway"
    env: str = os.getenv("ENV", "development")
    port: int = 8000
    log_level: str = "INFO"

    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://tantu:tantu@localhost:5432/tantu"
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # JWT
    jwt_public_key: str = os.getenv("JWT_PUBLIC_KEY", "")
    jwt_private_key: str = os.getenv("JWT_PRIVATE_KEY", "dev-only-key-replace-in-prod")
    jwt_issuer: str = os.getenv("JWT_ISSUER", "tantu")
    jwt_audience: str = os.getenv("JWT_AUDIENCE", "tantu-platform")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "RS256")
    jwt_leeway_s: int = 10

    # CORS
    cors_origins_raw: str = os.getenv("CORS_ORIGINS", "*")

    # Rate limit
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    # Downstream
    adapter_fabric_url: str = os.getenv("ADAPTER_FABRIC_URL", "http://localhost:8001")
    orchestrator_url: str = os.getenv("ORCHESTRATOR_URL", "http://localhost:8004")
    reasoning_copilot_url: str = os.getenv("REASONING_COPILOT_URL", "http://localhost:8003")
    edge_perception_url: str = os.getenv("EDGE_PERCEPTION_URL", "http://localhost:8002")
    downstream_timeout_s: float = float(os.getenv("DOWNSTREAM_TIMEOUT_S", "5.0"))

    # Helpers
    @property
    def cors_origins(self) -> list[str]:
        return _cors_origins(self.cors_origins_raw)

    @property
    def downstream_services(self) -> dict[str, str]:
        return {
            "adapter-fabric": self.adapter_fabric_url.rstrip("/"),
            "adapter_fabric": self.adapter_fabric_url.rstrip("/"),
            "orchestrator": self.orchestrator_url.rstrip("/"),
            "reasoning-copilot": self.reasoning_copilot_url.rstrip("/"),
            "reasoning_copilot": self.reasoning_copilot_url.rstrip("/"),
            "reasoning": self.reasoning_copilot_url.rstrip("/"),
            "edge-perception": self.edge_perception_url.rstrip("/"),
            "edge_perception": self.edge_perception_url.rstrip("/"),
            "edge": self.edge_perception_url.rstrip("/"),
        }

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
