"""Tier detection + settings. Offline-first, tiered."""

from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EdgeTier(str, Enum):
    PI5_HAILO = "pi5_hailo"
    ORIN_NANO = "orin_nano"
    THOR = "thor"


# Tier capabilities matrix — drives latency budgets, model selection, accel flags
TIER_CAPS: dict[str, dict[str, object]] = {
    EdgeTier.PI5_HAILO: {
        "accel": "hailo-8l",
        "gauge_budget_ms": 40.0,
        "fft_budget_ms": 20.0,
        "max_fps": 8,
        "hw_decoder": False,
        "description": "Raspberry Pi 5 + Hailo-8L (8 TOPS) — cost-optimized edge",
    },
    EdgeTier.ORIN_NANO: {
        "accel": "ampere-1024cuda",
        "gauge_budget_ms": 25.0,
        "fft_budget_ms": 12.0,
        "max_fps": 20,
        "hw_decoder": True,
        "description": "Jetson Orin Nano (40 TOPS) — balanced",
    },
    EdgeTier.THOR: {
        "accel": "blackwell-2070",
        "gauge_budget_ms": 12.0,
        "fft_budget_ms": 6.0,
        "max_fps": 60,
        "hw_decoder": True,
        "description": "Jetson Thor (2070 TFLOPS FP4) — flagship, full perception",
    },
}


def detect_tier(env_value: str | None = None) -> EdgeTier:
    """Tier detection: env EDGE_TIER wins, else auto-detect heuristics, else pi5_hailo default.

    Env values accepted (case-insensitive, dashes/underscores): pi5, pi5_hailo, hailo,
    orin, orin_nano, orin-nano, thor, jetson_thor.
    """
    raw = (env_value if env_value is not None else os.getenv("EDGE_TIER", "")).strip().lower()
    raw = raw.replace("-", "_")
    mapping: dict[str, EdgeTier] = {
        "pi5": EdgeTier.PI5_HAILO,
        "pi5_hailo": EdgeTier.PI5_HAILO,
        "hailo": EdgeTier.PI5_HAILO,
        "pi5hailo": EdgeTier.PI5_HAILO,
        "orin": EdgeTier.ORIN_NANO,
        "orin_nano": EdgeTier.ORIN_NANO,
        "orin_nano_8gb": EdgeTier.ORIN_NANO,
        "thor": EdgeTier.THOR,
        "jetson_thor": EdgeTier.THOR,
        "jetsonthor": EdgeTier.THOR,
    }
    if raw in mapping:
        return mapping[raw]
    # Heuristic fallback — inspect /proc/device-tree if present (best-effort, never raises)
    try:
        if os.path.exists("/proc/device-tree/model"):
            model = open("/proc/device-tree/model", "rb").read().decode(errors="ignore").lower()
            if "thor" in model:
                return EdgeTier.THOR
            if "orin" in model:
                return EdgeTier.ORIN_NANO
            if "raspberry" in model or "bcm2712" in model:
                return EdgeTier.PI5_HAILO
    except Exception:
        pass
    # env EDGE_TIER empty/unknown → default to cost tier
    return EdgeTier.PI5_HAILO


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    edge_tier: str = Field(default_factory=lambda: os.getenv("EDGE_TIER", "pi5_hailo"))
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_stream: str = Field(default="tantu:edge:readings")
    redis_max_buffer: int = Field(default=10000)
    jwt_secret: str = Field(default_factory=lambda: os.getenv("JWT_SECRET", os.getenv("JWT_PRIVATE_KEY", "dev-only-key-replace-in-prod")))
    jwt_algorithm: str = Field(default="HS256")
    ota_public_key_path: str = Field(default="")
    ota_current_version: str = Field(default="0.1.0")
    gauge_min_value: float = Field(default=0.0)
    gauge_max_value: float = Field(default=10.0)
    # dial geometry: angle where min sits (deg, 0=right, 90=down) and span clockwise
    gauge_min_angle_deg: float = Field(default=135.0)
    gauge_max_angle_deg: float = Field(default=45.0)  # implies 270° clockwise span (135→45 via 360)

    @property
    def tier(self) -> EdgeTier:
        return detect_tier(self.edge_tier)

    @property
    def tier_caps(self) -> dict[str, object]:
        return TIER_CAPS[self.tier]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
