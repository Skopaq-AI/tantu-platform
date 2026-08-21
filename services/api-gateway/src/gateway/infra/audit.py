"""Audit log — structlog JSON + Postgres persistence (best-effort)."""

from __future__ import annotations

import logging
import uuid

import structlog

from ..domain.models import AuditEntry
from .db import get_sessionmaker, AuditLogRow

log = structlog.get_logger("gateway.audit")
_pylog = logging.getLogger("gateway.audit")

_configured = False


def configure_structlog(level: str = "INFO") -> None:
    global _configured
    if _configured:
        return
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    _configured = True


async def write_audit(entry: AuditEntry) -> None:
    """Structured log + Postgres row. Never raises — best-effort."""
    try:
        # JSON log
        log.info(
            "audit",
            request_id=entry.request_id,
            principal=entry.principal,
            plant_id=entry.plant_id,
            method=entry.method,
            path=entry.path,
            status=entry.status,
            latency_ms=round(entry.latency_ms, 2),
            decision=entry.decision,
            reason=entry.reason,
        )
    except Exception as e:
        _pylog.warning("audit structlog failed: %s", e)

    try:
        Session = get_sessionmaker()
        async with Session() as session:
            row = AuditLogRow(
                request_id=entry.request_id,
                principal=entry.principal,
                plant_id=entry.plant_id,
                method=entry.method,
                path=entry.path,
                status=entry.status,
                latency_ms=entry.latency_ms,
                decision=entry.decision,
                reason=entry.reason,
            )
            session.add(row)
            await session.commit()
    except Exception as e:
        _pylog.debug("audit DB write skipped: %s", e)


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]
