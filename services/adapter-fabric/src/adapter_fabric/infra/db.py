"""Postgres persistence — SQLAlchemy async, best-effort table creation.

Table: adapter_configs — one row per AdapterConfig.
  adapter_id PK, protocol, station_id, enabled, tags_json (JSON), params_json (JSON),
  poll_interval_ms, created_at, updated_at

Pattern mirrors orchestrator/backend: best-effort init_db that never raises if DB
unreachable. SQLite fallback for tests.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Boolean, Integer, DateTime, JSON, func

from .config import settings

log = logging.getLogger("adapter_fabric.db")


class Base(DeclarativeBase):
    pass


class AdapterConfigRow(Base):
    __tablename__ = "adapter_configs"
    adapter_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    protocol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    station_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tags_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    params_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    poll_interval_ms: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


_engine: Optional[AsyncEngine] = None
_Session: Optional[async_sessionmaker[AsyncSession]] = None
_engine_url: Optional[str] = None


def _normalize_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def _create_engine(url: Optional[str] = None) -> AsyncEngine:
    db_url = _normalize_url(url or settings.database_url)
    if db_url.startswith("sqlite"):
        if "+aiosqlite" not in db_url:
            db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        # aiosqlite does not support pool_pre_ping with same semantics, but ok
        return create_async_engine(db_url, echo=False, future=True)
    return create_async_engine(db_url, pool_pre_ping=True, echo=False, future=True)


def get_engine(url: Optional[str] = None) -> AsyncEngine:
    global _engine, _engine_url
    requested = _normalize_url(url) if url else None
    if _engine is not None and requested is not None and _engine_url is not None and requested != _engine_url:
        # caller wants different DB – recreate (best-effort)
        try:
            pass
        except Exception:
            pass
        _engine = _create_engine(url)
        _engine_url = requested
        return _engine
    if _engine is None:
        _engine = _create_engine(url)
        _engine_url = _normalize_url(url) if url else _normalize_url(settings.database_url)
    return _engine


def get_sessionmaker(url: Optional[str] = None) -> async_sessionmaker[AsyncSession]:
    global _Session
    if _Session is None:
        _Session = async_sessionmaker(get_engine(url), expire_on_commit=False, class_=AsyncSession)
    return _Session


async def init_db(url: Optional[str] = None) -> None:
    """Create adapter_configs table if reachable — never raises."""
    try:
        engine = get_engine(url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.info("adapter-fabric db: adapter_configs ready")
    except Exception as e:
        log.warning("adapter-fabric db: init skipped (DB unreachable): %s", e)


async def close_db() -> None:
    global _engine, _Session, _engine_url
    if _engine is not None:
        try:
            await _engine.dispose()
        except Exception:
            pass
        _engine = None
    _Session = None
    _engine_url = None


def reset_engine() -> None:
    global _engine, _Session, _engine_url
    _engine = None
    _Session = None
    _engine_url = None
