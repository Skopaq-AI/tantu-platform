"""TimescaleDB — SQLAlchemy async, hypertable setup."""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, Text, DateTime, func, JSON, Index
from datetime import datetime

from .config import settings

log = logging.getLogger("orchestrator.db")


class Base(DeclarativeBase):
    pass


class DefectEventRow(Base):
    __tablename__ = "defect_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    plant_id: Mapped[str] = mapped_column(String(64), index=True)
    station_id: Mapped[str] = mapped_column(String(128))
    track: Mapped[str] = mapped_column(String(16))
    defect_class: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float)
    latency_ms: Mapped[float] = mapped_column(Float)
    protocol: Mapped[str] = mapped_column(String(32))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    adapter_id: Mapped[str] = mapped_column(String(64), default="")


class CorrelationReportRow(Base):
    __tablename__ = "correlation_reports"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    plant_id: Mapped[str] = mapped_column(String(64), index=True)
    summary: Mapped[str] = mapped_column(Text)
    contributing: Mapped[list] = mapped_column(JSON, default=list)  # JSONB
    confidence: Mapped[float] = mapped_column(Float)
    tokens_in: Mapped[int] = mapped_column(Integer)
    tokens_out: Mapped[int] = mapped_column(Integer)
    cost_usd: Mapped[float] = mapped_column(Float)
    window_size: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class IdempotencyRow(Base):
    __tablename__ = "idempotency_keys"
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    response: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


_engine: Optional[AsyncEngine] = None
_Session = None


def _normalize_url(url: str) -> str:
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
    """Create tables + hypertables (best-effort, logs but never raises on missing DB)."""
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            # Timescale hypertable — ignore if extension not present
            try:
                from sqlalchemy import text
                await conn.execute(text("SELECT create_hypertable('defect_events','ts', if_not_exists=>TRUE, migrate_data=>TRUE)"))
                await conn.execute(text("SELECT create_hypertable('correlation_reports','created_at', if_not_exists=>TRUE, migrate_data=>TRUE)"))
            except Exception as e:
                log.debug("hypertable creation skipped: %s", e)
        log.info("orchestrator db: tables ready")
    except Exception as e:
        log.warning("orchestrator db: init skipped (DB unreachable): %s", e)


async def close_db() -> None:
    global _engine
    if _engine is not None:
        try:
            await _engine.dispose()
        except Exception:
            pass
        _engine = None
