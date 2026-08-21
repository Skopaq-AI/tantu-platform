"""Postgres — SQLAlchemy async, best-effort audit log table."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, Text, DateTime, func
from datetime import datetime

from .config import settings

log = logging.getLogger("gateway.db")


class Base(DeclarativeBase):
    pass


class AuditLogRow(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    principal: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    plant_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    method: Mapped[str] = mapped_column(String(16))
    path: Mapped[str] = mapped_column(Text)
    status: Mapped[int] = mapped_column(Integer)
    latency_ms: Mapped[float] = mapped_column(Float)
    decision: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


_engine: Optional[AsyncEngine] = None
_Session = None


def _normalize_url(url: str) -> str:
    # psycopg async driver expects postgresql+psycopg://, but SQLAlchemy async needs same
    # if URL is sync postgresql://, convert
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        url = _normalize_url(settings.database_url)
        _engine = create_async_engine(url, pool_pre_ping=True, echo=False)
    return _engine


def get_sessionmaker():
    global _Session
    if _Session is None:
        _Session = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _Session


async def init_db() -> None:
    """Create audit_logs table if reachable — never raises."""
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.info("gateway db: audit_logs ready")
    except Exception as e:
        log.warning("gateway db: init skipped (DB unreachable): %s", e)


async def close_db() -> None:
    global _engine
    if _engine is not None:
        try:
            await _engine.dispose()
        except Exception:
            pass
        _engine = None
