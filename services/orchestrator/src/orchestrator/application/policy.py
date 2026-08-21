"""Application — policy facade (thin wrapper over domain policy for DI)."""

from __future__ import annotations

from ..domain.policies import EventWindowPolicy
from ..infra.config import settings


def get_policy(
    confidence_threshold: float | None = None,
    max_size: int | None = None,
    ttl_s: float | None = None,
) -> EventWindowPolicy:
    return EventWindowPolicy(
        confidence_threshold=confidence_threshold
        if confidence_threshold is not None
        else settings.confidence_threshold,
        max_size=max_size if max_size is not None else settings.window_size,
        ttl_s=ttl_s if ttl_s is not None else settings.window_ttl_s,
    )
