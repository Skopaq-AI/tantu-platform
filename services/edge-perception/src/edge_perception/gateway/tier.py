"""Tier helpers — re-export for gateway."""

from ..config import EdgeTier, TIER_CAPS, detect_tier


def get_tier(env_value: str | None = None) -> EdgeTier:
    return detect_tier(env_value)


def tier_caps(tier: EdgeTier) -> dict:
    return TIER_CAPS[tier]
