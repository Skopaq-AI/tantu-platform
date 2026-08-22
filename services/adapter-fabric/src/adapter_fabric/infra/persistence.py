"""Persistence helpers — AdapterConfig ↔ adapter_configs row.

Best-effort: every function catches exceptions and logs at debug, never raises
to caller. This keeps the registry usable when Postgres is down (e.g. in tests
or during rolling deploy before secret is mounted).
"""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import select, delete

from ..domain.models import AdapterConfig, TagMapping, Protocol
from .db import get_sessionmaker, AdapterConfigRow

log = logging.getLogger("adapter_fabric.persistence")


# ---------------------------------------------------------------------------
# serialization helpers
# ---------------------------------------------------------------------------

def _tags_to_json(tags: tuple[TagMapping, ...]) -> list[dict]:
    return [
        {
            "source_tag": t.source_tag,
            "metric": t.metric,
            "unit": t.unit,
            "scale": t.scale,
            "offset": t.offset,
            "data_type": t.data_type,
            "compound_formula": t.compound_formula,
            "source_tags": t.source_tags,
        }
        for t in tags
    ]


def _json_to_tags(raw: Optional[list]) -> tuple[TagMapping, ...]:
    if not raw:
        return ()
    out: list[TagMapping] = []
    for d in raw:
        try:
            out.append(
                TagMapping(
                    source_tag=str(d.get("source_tag", "")),
                    metric=str(d.get("metric", "")),
                    unit=str(d.get("unit", "")),
                    scale=float(d.get("scale", 1.0)),
                    offset=float(d.get("offset", 0.0)),
                    data_type=str(d.get("data_type", "float")),
                    compound_formula=d.get("compound_formula"),
                    source_tags=d.get("source_tags"),
                )
            )
        except Exception as e:
            log.debug("skip malformed tag row: %s (%s)", d, e)
            continue
    return tuple(out)


def _row_to_config(row: AdapterConfigRow) -> AdapterConfig:
    try:
        proto = Protocol(row.protocol)
    except ValueError:
        # unknown protocol string stored — keep as string enum fallback
        # construct via try; if fails default to opcua and store original in params
        try:
            proto = Protocol(row.protocol.lower())  # type: ignore
        except Exception:
            proto = Protocol.OPCUA  # type: ignore
    tags = _json_to_tags(row.tags_json)
    return AdapterConfig(
        adapter_id=row.adapter_id,
        protocol=proto,
        station_id=row.station_id,
        enabled=bool(row.enabled),
        tags=tags,
        params=dict(row.params_json or {}),
        poll_interval_ms=int(row.poll_interval_ms),
    )


def _config_to_row(cfg: AdapterConfig) -> AdapterConfigRow:
    proto_val = cfg.protocol.value if hasattr(cfg.protocol, "value") else str(cfg.protocol)
    return AdapterConfigRow(
        adapter_id=cfg.adapter_id,
        protocol=str(proto_val),
        station_id=cfg.station_id,
        enabled=bool(cfg.enabled),
        tags_json=_tags_to_json(cfg.tags),
        params_json=dict(cfg.params or {}),
        poll_interval_ms=int(cfg.poll_interval_ms),
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

async def save_adapter_config(cfg: AdapterConfig) -> bool:
    """Dual-write AdapterConfig to Postgres and Redis tantu:adapters.

    Both writes are best-effort but attempted regardless of the other's
    outcome, so a transient PG outage still leaves Redis durable (and vice
    versa). Returns True if at least one backend succeeded.
    """
    pg_ok = False
    try:
        Session = get_sessionmaker()
        async with Session() as session:
            row = _config_to_row(cfg)
            await session.merge(row)
            await session.commit()
            pg_ok = True
    except Exception as e:
        log.debug("save_adapter_config postgres skipped: %s", e)
        pg_ok = False
    # always attempt Redis dual-write even if PG succeeded — keeps tantu:adapters in sync
    redis_ok = False
    try:
        redis_ok = await _redis_save(cfg)
    except Exception as e:
        log.debug("save_adapter_config redis dual-write: %s", e)
        redis_ok = False
    if pg_ok and redis_ok:
        log.debug("save_adapter_config dual-write ok: %s", cfg.adapter_id)
    elif pg_ok or redis_ok:
        log.debug("save_adapter_config partial write pg=%s redis=%s id=%s", pg_ok, redis_ok, cfg.adapter_id)
    return pg_ok or redis_ok


async def delete_adapter_config(adapter_id: str) -> bool:
    """Delete from both Postgres and Redis tantu:adapters (dual-delete)."""
    pg_ok = False
    try:
        Session = get_sessionmaker()
        async with Session() as session:
            await session.execute(delete(AdapterConfigRow).where(AdapterConfigRow.adapter_id == adapter_id))
            await session.commit()
            pg_ok = True
    except Exception as e:
        log.debug("delete_adapter_config postgres skipped: %s", e)
        pg_ok = False
    # also delete from redis hash — always attempt even if PG failed
    redis_ok = False
    try:
        r = _get_redis_client()
        if r is not None:
            await r.hdel("tantu:adapters", adapter_id)
            try:
                if hasattr(r, "aclose"):
                    await r.aclose()  # type: ignore
                else:
                    await r.close()  # type: ignore
            except Exception:
                pass
            redis_ok = True
    except Exception as e:
        log.debug("delete_adapter_config redis dual-delete: %s", e)
    return pg_ok or redis_ok


def _get_redis_client():  # type: ignore
    """Return an async Redis client for dual-write hash tantu:adapters.

    Honors REDIS_URL env (e.g. redis://10.30.0.3:6379/0 for real DB) and
    settings.redis_url; falls back to in-cluster redis:6379 only when the
    URL is missing or still a Secret Manager placeholder (REPLACE_ME).
    The previous hardcoded check for 10.30.49.75 is removed — that was a
    stale Memorystore IP and caused prod writes to be silently dropped.
    """
    try:
        import os

        import redis.asyncio as aioredis  # type: ignore

        from .config import settings as _settings

        url = os.environ.get("REDIS_URL") or getattr(_settings, "redis_url", "") or "redis://redis:6379/0"
        if not url or "REPLACE_ME" in url:
            url = "redis://redis:6379/0"
        return aioredis.from_url(url, decode_responses=True)
    except Exception:
        return None


async def _redis_save(cfg: AdapterConfig) -> bool:
    try:
        r = _get_redis_client()
        if r is None:
            return False
        import json

        payload = {
            "adapter_id": cfg.adapter_id,
            "protocol": cfg.protocol.value if hasattr(cfg.protocol, "value") else str(cfg.protocol),
            "station_id": cfg.station_id,
            "enabled": bool(cfg.enabled),
            "poll_interval_ms": int(cfg.poll_interval_ms),
            "params": dict(cfg.params or {}),
            "tags": _tags_to_json(cfg.tags),
        }
        await r.hset("tantu:adapters", cfg.adapter_id, json.dumps(payload))
        try:
            if hasattr(r, "aclose"):
                await r.aclose()  # type: ignore
            else:
                await r.close()  # type: ignore
        except Exception:
            pass
        return True
    except Exception as e:
        log.debug("redis save dual-write failed: %s", e)
        return False


async def _redis_load() -> List[AdapterConfig]:
    try:
        r = _get_redis_client()
        if r is None:
            return []
        data = await r.hgetall("tantu:adapters")
        try:
            if hasattr(r, "aclose"):
                await r.aclose()  # type: ignore
            else:
                await r.close()  # type: ignore
        except Exception:
            pass
        out: List[AdapterConfig] = []
        if not data:
            return []
        import json

        for _k, v in data.items():
            try:
                d = json.loads(v) if isinstance(v, str) else json.loads(v.decode() if isinstance(v, bytes) else v)
                proto_val = d.get("protocol", "opcua")
                try:
                    proto = Protocol(proto_val)
                except Exception:
                    try:
                        proto = Protocol(str(proto_val).lower())  # type: ignore
                    except Exception:
                        proto = Protocol.OPCUA  # type: ignore
                tags = _json_to_tags(d.get("tags"))
                out.append(
                    AdapterConfig(
                        adapter_id=d["adapter_id"],
                        protocol=proto,
                        station_id=d.get("station_id", ""),
                        enabled=bool(d.get("enabled", True)),
                        tags=tags,
                        params=dict(d.get("params") or {}),
                        poll_interval_ms=int(d.get("poll_interval_ms", 1000)),
                    )
                )
            except Exception as e:
                log.debug("redis load skip %s: %s", _k, e)
                continue
        return out
    except Exception as e:
        log.debug("redis load fallback: %s", e)
        return []


async def load_adapter_configs() -> List[AdapterConfig]:
    """Load all persisted configs. Returns [] if DB unreachable.

    Tries Postgres first; if empty or unreachable, falls back to Redis
    tantu:adapters hash. Dual-write keeps both backends in sync, so either
    can be used for restore_from_db on startup.
    """
    # Try Postgres
    try:
        Session = get_sessionmaker()
        async with Session() as session:
            res = await session.execute(select(AdapterConfigRow))
            rows = res.scalars().all()
            configs: List[AdapterConfig] = []
            for r in rows:
                try:
                    configs.append(_row_to_config(r))
                except Exception as e:
                    log.debug("skip row %s: %s", getattr(r, "adapter_id", "?"), e)
                    continue
            if configs:
                return configs
            # if postgres returned 0, try redis (may have been written via fallback before DB was fixed)
            redis_cfgs = await _redis_load()
            if redis_cfgs:
                log.info("load_adapter_configs: %d from redis fallback", len(redis_cfgs))
                return redis_cfgs
            return configs
    except Exception as e:
        log.debug("load_adapter_configs postgres fallback: %s", e)
        # Try redis
        redis_cfgs = await _redis_load()
        if redis_cfgs:
            return redis_cfgs
        return []


async def get_adapter_config(adapter_id: str) -> Optional[AdapterConfig]:
    try:
        Session = get_sessionmaker()
        async with Session() as session:
            res = await session.execute(select(AdapterConfigRow).where(AdapterConfigRow.adapter_id == adapter_id))
            row = res.scalar_one_or_none()
            if row is None:
                return None
            return _row_to_config(row)
    except Exception as e:
        log.debug("get_adapter_config fallback: %s", e)
        return None
