"""Central settings — 12-factor, env-driven."""

from __future__ import annotations

import os
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # service
    service_name: str = "reasoning-copilot"
    service_version: str = "0.2.0"
    port: int = 8003
    log_level: str = "info"
    # GENAI — Gemini
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = Field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
    )
    gemini_grounded: bool = True
    # Nemotron on-prem
    nemotron_vllm_url: str = Field(
        default_factory=lambda: os.getenv("VLLM_URL", "http://localhost:8000/v1/chat/completions")
    )
    nemotron_ollama_url: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
    )
    nemotron_model: str = Field(default_factory=lambda: os.getenv("NEMOTRON_MODEL", "nemotron-9b"))
    nemotron_prefer: str = Field(
        default_factory=lambda: os.getenv("NEMOTRON_PREFER", "vllm")
    )  # vllm | ollama
    air_gapped_default: bool = False
    # RAG / Qdrant
    qdrant_url: str = Field(
        default_factory=lambda: os.getenv("QDRANT_URL", "http://localhost:6333")
    )
    qdrant_collection: str = Field(
        default_factory=lambda: os.getenv("QDRANT_COLLECTION", "tantu_runbooks")
    )
    qdrant_api_key: str = Field(default_factory=lambda: os.getenv("QDRANT_API_KEY", ""))
    embedding_model: str = Field(
        default_factory=lambda: os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        )
    )
    embedding_dim: int = 384
    chunk_size: int = 800
    chunk_overlap: int = 120
    # costing — Business Plan rates
    gemini_in_per_m: float = 2.0  # $2 / M input tokens
    gemini_out_per_m: float = 10.0  # $10 / M output tokens
    # security
    jwt_secret: str = Field(
        default_factory=lambda: os.getenv(
            "JWT_PRIVATE_KEY", os.getenv("JWT_SECRET", "dev-only-key-replace-in-prod")
        )
    )
    jwt_alg: str = "HS256"
    # rate limit
    rate_limit_per_min: int = 60
    rate_limit_window_s: int = 60
    # vernacular
    tts_url: str = Field(default_factory=lambda: os.getenv("TTS_URL", ""))
    stt_url: str = Field(default_factory=lambda: os.getenv("STT_URL", ""))
    # telemetry
    otel_endpoint: str = Field(default_factory=lambda: os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", ""))

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
