"""Persistence — TimescaleDB via SQLAlchemy async, with graceful degradation."""

from __future__ import annotations

import logging
from typing import Optional, List

from sqlalchemy import select, desc
from sqlalchemy.exc import IntegrityError

from ..domain.events import DefectEvent, CorrelationReport
from .db import get_sessionmaker, DefectEventRow, CorrelationReportRow

log = logging.getLogger("orchestrator.persistence")


async def persist_event(event: DefectEvent) -> bool:
    """Insert defect event; returns False if duplicate or DB down."""
    try:
        Session = get_sessionmaker()
        async with Session() as session:
            row = DefectEventRow(
                id=event.event_id,
                plant_id=event.plant_id,
                station_id=event.station_id,
                track=event.track.value,
                defect_class=event.defect_class.value,
                confidence=event.confidence,
                latency_ms=event.latency_ms,
                protocol=event.protocol,
                adapter_id=event.adapter_id,
            )
            session.add(row)
            await session.commit()
            return True
    except IntegrityError:
        # duplicate
        return False
    except Exception as e:
        log.debug("persist_event skipped: %s", e)
        return False


async def persist_report(report: CorrelationReport) -> bool:
    try:
        Session = get_sessionmaker()
        async with Session() as session:
            row = CorrelationReportRow(
                id=report.id,
                plant_id=report.plant_id,
                summary=report.summary,
                contributing=report.contributing,
                confidence=report.confidence,
                tokens_in=report.tokens_in,
                tokens_out=report.tokens_out,
                cost_usd=report.cost_usd,
                window_size=report.window_size,
            )
            session.add(row)
            await session.commit()
            return True
    except IntegrityError:
        return False
    except Exception as e:
        log.debug("persist_report skipped: %s", e)
        return False


async def list_reports(limit: int = 50, plant_id: Optional[str] = None) -> List[CorrelationReport]:
    try:
        Session = get_sessionmaker()
        async with Session() as session:
            q = (
                select(CorrelationReportRow)
                .order_by(desc(CorrelationReportRow.created_at))
                .limit(limit)
            )
            if plant_id:
                q = q.where(CorrelationReportRow.plant_id == plant_id)
            res = await session.execute(q)
            rows = res.scalars().all()
            reports: List[CorrelationReport] = []
            for r in rows:
                reports.append(
                    CorrelationReport(
                        id=r.id,
                        plant_id=r.plant_id,
                        summary=r.summary,
                        contributing=r.contributing or [],
                        confidence=r.confidence,
                        tokens_in=r.tokens_in,
                        tokens_out=r.tokens_out,
                        cost_usd=r.cost_usd,
                        window_size=r.window_size,
                    )
                )
            return reports
    except Exception as e:
        log.debug("list_reports fallback: %s", e)
        return []


async def get_report(report_id: str) -> Optional[CorrelationReport]:
    try:
        Session = get_sessionmaker()
        async with Session() as session:
            q = select(CorrelationReportRow).where(CorrelationReportRow.id == report_id)
            res = await session.execute(q)
            r = res.scalar_one_or_none()
            if not r:
                return None
            return CorrelationReport(
                id=r.id,
                plant_id=r.plant_id,
                summary=r.summary,
                contributing=r.contributing or [],
                confidence=r.confidence,
                tokens_in=r.tokens_in,
                tokens_out=r.tokens_out,
                cost_usd=r.cost_usd,
                window_size=r.window_size,
            )
    except Exception as e:
        log.debug("get_report fallback: %s", e)
        return None
