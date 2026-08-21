"""DB — SQLAlchemy 2.0 + async, multi-tenant models with org isolation."""
from __future__ import annotations

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine as _sa_create_async_engine, async_sessionmaker, AsyncEngine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Float, Integer, Boolean, DateTime, Text, ForeignKey, JSON, Index, func, UniqueConstraint

log = logging.getLogger("tantu.db")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://tantu:tantu@localhost:5432/tantu")
# Also support DATABASE_URL env with sync driver; normalize to async
def _normalize_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url

# ── Base ─────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass

def _uuid() -> str:
    return uuid.uuid4().hex

def _now() -> datetime:
    return datetime.now(timezone.utc)

# ── Models ─────────────────────────────────────────────────────────────────
class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class Plant(Base):
    __tablename__ = "plants"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    org_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    meta_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_plant_org_name"),)

class Line(Base):
    __tablename__ = "lines"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    plant_id: Mapped[str] = mapped_column(String(64), ForeignKey("plants.id", ondelete="CASCADE"), index=True, nullable=False)
    org_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Station(Base):
    __tablename__ = "stations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    line_id: Mapped[str] = mapped_column(String(64), ForeignKey("lines.id", ondelete="CASCADE"), index=True, nullable=False)
    plant_id: Mapped[str] = mapped_column(String(64), ForeignKey("plants.id", ondelete="CASCADE"), index=True, nullable=False)
    org_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    station_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # opcua, modbus, camera, etc.
    protocol: Mapped[str] = mapped_column(String(64), default="opcua")
    config_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class Membership(Base):
    """User ↔ Organization role + ABAC plant_ids JSON."""
    __tablename__ = "memberships"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    org_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)  # one of ROLES canonical
    plant_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)  # list[str] or ["*"]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    __table_args__ = (
        UniqueConstraint("user_id", "org_id", name="uq_membership_user_org"),
        Index("ix_membership_org_role", "org_id", "role"),
    )

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    org_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)  # hash of jti or token
    jti: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Invitation(Base):
    __tablename__ = "invitations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    org_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(320), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    plant_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    token_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    invited_by: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ApiKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    org_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    plant_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)  # first 8 chars for display
    scopes: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class AuditLog(Base):
    """Org-isolated audit log."""
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    org_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("organizations.id", ondelete="SET NULL"), index=True, nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    principal: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)  # sub
    plant_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)  # login, invite, ingest, etc.
    resource: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    method: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    decision: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # allow/deny
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)
    __table_args__ = (
        Index("ix_audit_org_created", "org_id", "created_at"),
        Index("ix_audit_principal", "principal"),
    )

class DefectEventRow(Base):
    __tablename__ = "defect_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    station_id: Mapped[str] = mapped_column(String(64), nullable=False)
    defect_class: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    # org isolation added
    org_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    plant_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    protocol: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

# ── Engine & session handling ────────────────────────────────────────────
_engine: Optional[AsyncEngine] = None
_Session: Optional[async_sessionmaker[AsyncSession]] = None
_engine_url: Optional[str] = None

def _create_engine(url: Optional[str] = None) -> AsyncEngine:
    db_url = _normalize_url(url or DATABASE_URL)
    # Handle sqlite for tests: sqlite+aiosqlite
    if db_url.startswith("sqlite"):
        # ensure async driver
        if "+aiosqlite" not in db_url:
            db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    # sqlite does not support pool_pre_ping with aiosqlite
    if db_url.startswith("sqlite"):
        engine = _sa_create_async_engine(db_url, echo=False, future=True)
    else:
        engine = _sa_create_async_engine(db_url, pool_pre_ping=True, echo=False, future=True)
    return engine

def create_async_engine(url: Optional[str] = None) -> AsyncEngine:
    """Public factory for tests / callers."""
    return _create_engine(url)

def get_engine(url: Optional[str] = None) -> AsyncEngine:
    global _engine, _engine_url
    requested = _normalize_url(url) if url else None
    # If engine exists but caller requests different URL, recreate
    if _engine is not None and requested is not None and _engine_url is not None and requested != _engine_url:
        # caller wants different DB; dispose old and recreate
        try:
            # async dispose cannot be called here sync; will be handled by init_db/close_db path
            pass
        except Exception:
            pass
        # For sync recreation, we replace engine (best-effort)
        _engine = _create_engine(url)
        _engine_url = requested
        return _engine
    if _engine is None:
        _engine = _create_engine(url)
        _engine_url = _normalize_url(url) if url else _normalize_url(DATABASE_URL)
    return _engine

def get_sessionmaker(url: Optional[str] = None) -> async_sessionmaker[AsyncSession]:
    global _Session
    if _Session is None:
        _Session = async_sessionmaker(get_engine(url), expire_on_commit=False, class_=AsyncSession)
    return _Session

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields async session."""
    Session = get_sessionmaker()
    async with Session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db(url: Optional[str] = None) -> None:
    """Create all tables. Best-effort; never raises in prod if DB unreachable."""
    try:
        engine = get_engine(url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.info("db: tables ready")
    except Exception as e:
        log.warning("db: init skipped (DB unreachable): %s", e)

async def close_db() -> None:
    global _engine, _Session, _engine_url
    if _engine is not None:
        try:
            await _engine.dispose()
        except Exception:
            pass
        _engine = None
    _Session = None

# Sync helper for scripts/tests
def reset_engine():
    global _engine, _Session, _engine_url
    _engine = None
    _Session = None
    _engine_url = None
