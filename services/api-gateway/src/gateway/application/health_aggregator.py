"""Health aggregator — fans out to downstream /health in parallel."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from ..infra.config import settings
from ..infra.downstream import downstream_client


async def aggregate_health() -> dict[str, Any]:
    services = settings.downstream_services
    # Deduplicate by base URL
    seen: set[str] = set()
    unique: dict[str, str] = {}
    for name, url in services.items():
        if url not in seen:
            seen.add(url)
            unique[name] = url

    started = time.time()
    tasks = [downstream_client.health_check(url, "/health") for url in unique.values()]
    # Also check self? caller adds
    results = await asyncio.gather(*tasks, return_exceptions=True)

    downstream: dict[str, Any] = {}
    overall_ok = True
    for (name, url), res in zip(unique.items(), results):
        if isinstance(res, Exception):
            downstream[name] = {"url": url, "status": "down", "error": str(res)[:200]}
            overall_ok = False
        else:
            downstream[name] = res
            if res.get("status") not in ("ok",):
                # allow degraded but mark overall as degraded not down — gateway stays up
                if res.get("status") == "down":
                    overall_ok = False

    latency_ms = (time.time() - started) * 1000
    return {
        "status": "ok" if overall_ok else "degraded",
        "service": "api-gateway",
        "ts": time.time(),
        "frames_never_leave": True,
        "latency_ms": round(latency_ms, 2),
        "downstream": downstream,
    }
