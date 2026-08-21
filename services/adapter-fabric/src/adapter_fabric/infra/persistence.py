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
    """Upsert one AdapterConfig. Returns True if persisted, False if DB down."""
    # try postgres first
    pg_ok = False
    try:
        Session = get_sessionmaker()
        async with Session() as session:
            # merge does upsert on PK
            row = _config_to_row(cfg)
            await session.merge(row)
            await session.commit()
            pg_ok = True
    except Exception as e:
        log.debug("save_adapter_config postgres skipped: %s", e)
        pg_ok = False
    # also save to redis fallback (best-effort, always). If pg failed, redis is the durability.
    try:
        redis_ok = await _redis_save(cfg)
        return pg_ok or redis_ok
    except Exception as e:
        log.debug("save_adapter_config redis fallback: %s", e)
        return pg_ok


async def delete_adapter_config(adapter_id: str) -> bool:
    """Delete one row. Returns True if attempted (or not found), False if DB down."""
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
    # also delete from redis hash
    try:
        r = _get_redis_client()
        if r is not None:
            await r.hdel("tantu:adapters", adapter_id)
            await r.close()
            return True
    except Exception as e:
        log.debug("delete_adapter_config redis fallback: %s", e)
    return pg_ok


def _get_redis_client():  # type: ignore
    try:
        import os

        import redis.asyncio as aioredis  # type: ignore

        url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        # also fallback to secret-derived host if REDIS_URL missing
        if not url or "REPLACE_ME" in url or "10.30.49.75" in url:
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
        # short expiry none — persist until delete
        await r.close()
        return True
    except Exception as e:
        log.debug("redis save fallback failed: %s", e)
        return False


async def _redis_load() -> List[AdapterConfig]:
    try:
        r = _get_redis_client()
        if r is None:
            return []
        data = await r.hgetall("tantu:adapters")
        await r.close()
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
    (in-cluster `redis:6379` — used when Secret Manager still has REPLACE_ME).
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
