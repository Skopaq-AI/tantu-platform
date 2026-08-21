"""Idempotency store — Postgres primary + in-memory fallback (pure async).

Keys are stable dedupe_key (event_id) or composite (plant_id + window hash).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional, Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .db import get_sessionmaker, IdempotencyRow

log = logging.getLogger("orchestrator.idempotency")


class IdempotencyStore:
    """Provides check_and_set semantics."""

    def __init__(self) -> None:
        self._mem: dict[str, tuple[Any, float]] = {}
        self._lock = asyncio.Lock()
        self._ttl_s = 3600.0

    async def exists(self, key: str) -> bool:
        # Try DB first
        try:
            Session = get_sessionmaker()
            async with Session() as s:
                q = select(IdempotencyRow).where(IdempotencyRow.key == key)
                r = await s.execute(q)
                if r.scalar_one_or_none() is not None:
                    return True
        except Exception as e:
            log.debug("idempotency exists DB fallback: %s", e)
        # Fallback mem
        async with self._lock:
            # prune expired
            now = time.time()
            expired = [k for k, (_, ts) in self._mem.items() if now - ts > self._ttl_s]
            for k in expired:
                self._mem.pop(k, None)
            return key in self._mem

    async def get(self, key: str) -> Optional[Any]:
        try:
            Session = get_sessionmaker()
            async with Session() as s:
                q = select(IdempotencyRow).where(IdempotencyRow.key == key)
                r = await s.execute(q)
                row = r.scalar_one_or_none()
                if row is not None:
                    return row.response
        except Exception as e:
            log.debug("idempotency get fallback: %s", e)
        async with self._lock:
            v = self._mem.get(key)
            if v:
                return v[0]
        return None

    async def put(self, key: str, response: Any) -> bool:
        """Insert if not exists. Returns True if inserted, False if duplicate."""
        # Try DB
        try:
            Session = get_sessionmaker()
            async with Session() as s:
                row = IdempotencyRow(key=key, response=response)
                s.add(row)
                await s.commit()
                return True
        except IntegrityError:
            return False
        except Exception as e:
            log.debug("idempotency put DB fallback: %s", e)
        # Mem fallback
        async with self._lock:
            if key in self._mem:
                return False
            self._mem[key] = (response, time.time())
            return True

    async def check_or_put(self, key: str, response: Any) -> tuple[bool, Optional[Any]]:
        """Atomic check: if exists return (False, existing), else put and return (True, None)."""
        existing = await self.get(key)
        if existing is not None:
            return False, existing
        ok = await self.put(key, response)
        if not ok:
            # race — fetch existing
            existing = await self.get(key)
            return False, existing
        return True, None

    async def clear(self) -> None:
        async with self._lock:
            self._mem.clear()
        try:
            Session = get_sessionmaker()
            async with Session() as s:
                from sqlalchemy import delete

                await s.execute(delete(IdempotencyRow))
                await s.commit()
        except Exception:
            pass


idempotency_store = IdempotencyStore()
