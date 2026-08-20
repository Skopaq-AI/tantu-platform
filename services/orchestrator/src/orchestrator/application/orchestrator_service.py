"""Application — orchestrator service: window → policy → reasoning → persistence → idempotency."""
from __future__ import annotations

import logging
import time
from typing import Optional, List

from ..domain.events import DefectEvent, CorrelationReport
from ..domain.policies import EventWindowPolicy
from ..infra.reasoning_client import reasoning_client
from ..infra.persistence import persist_event, persist_report
from ..infra.idempotency import idempotency_store
from ..infra.nats_bus import nats_bus

log = logging.getLogger("orchestrator.service")


class OrchestratorService:
    """Coordinates the escalation workflow.

    - Idempotent ingest (dedupe by event_id).
    - Window policy (per-plant).
    - Reasoning call + report emission + persistence.
    """

    def __init__(self, policy: EventWindowPolicy):
        self.policy = policy
        # in-memory report cache for read fallback when DB down
        self._reports: list[CorrelationReport] = []
        self._seen_events: set[str] = set()

    async def ingest(self, event: DefectEvent) -> tuple[bool, Optional[CorrelationReport]]:
        """Ingest one event. Returns (escalated, report_or_none).

        Idempotency: duplicate event_id returns previous escalation result without reprocessing.
        """
        dedupe_key = f"event:{event.event_id}"
        existing = await idempotency_store.get(dedupe_key)
        if existing is not None:
            # Already processed — return what we returned before
            escalated = bool(existing.get("escalated"))
            report_dict = existing.get("report")
            report = None
            if report_dict:
                try:
                    report = CorrelationReport(**report_dict)
                except Exception:
                    report = None
            log.info("orchestrator deduplicated %s", event.event_id)
            return escalated, report

        # Persist event (best-effort)
        await persist_event(event)

        # Window ingest
        self.policy.ingest(event)
        pid = event.plant_id

        # Check escalation
        if not self.policy.should_escalate_for(pid):
            # Record idempotent no-escalation
            await idempotency_store.put(dedupe_key, {"escalated": False, "report": None})
            return False, None

        # Escalate — pop window for this plant
        window_events = self.policy.pop_window(pid)
        if not window_events:
            window_events = [event]

        # Idempotency for report — ensure we don't double-correlate same window
        # Use deterministic key: plant + sorted event_ids
        window_key_sorted = ",".join(sorted(e.event_id for e in window_events))
        report_key = f"report:{pid}:{hash(window_key_sorted) & 0xffffffff:08x}"
        existing_report = await idempotency_store.get(report_key)
        if existing_report is not None:
            rep_dict = existing_report.get("report")
            report = CorrelationReport(**rep_dict) if rep_dict else None
            await idempotency_store.put(dedupe_key, {"escalated": True, "report": rep_dict})
            return True, report

        # Call reasoning plane
        try:
            report = await reasoning_client.correlate(window_events, plant_id=pid)
        except Exception as e:
            log.warning("reasoning correlate failed: %s", e)
            report = CorrelationReport(
                plant_id=pid,
                summary=f"Escalated {len(window_events)} fault(s) — reasoning unavailable",
                contributing=[e.station_id for e in window_events],
                confidence=max((e.confidence for e in window_events), default=0.9),
                tokens_in=0,
                tokens_out=0,
                cost_usd=0.0,
                window_size=len(window_events),
            )

        # Persist + publish
        await persist_report(report)
        self._reports.append(report)
        # Keep only recent 200 in memory
        if len(self._reports) > 200:
            self._reports = self._reports[-200:]

        try:
            await nats_bus.publish_report(None, report.to_dict())
        except Exception as e:
            log.debug("publish report skipped: %s", e)

        # Record both idempotency keys
        report_dict = report.to_dict()
        await idempotency_store.put(report_key, {"escalated": True, "report": report_dict})
        await idempotency_store.put(dedupe_key, {"escalated": True, "report": report_dict})

        log.info("orchestrator escalated plant %s with %d events → %s", pid, len(window_events), report.id)
        return True, report

    async def ingest_batch(self, events: List[DefectEvent]) -> List[tuple[bool, Optional[CorrelationReport]]]:
        results = []
        for e in events:
            results.append(await self.ingest(e))
        return results

    def window_snapshot(self) -> dict:
        return self.policy.window_sizes()

    def reports_memory(self) -> list[CorrelationReport]:
        return list(self._reports)

    def clear(self) -> None:
        self.policy.clear()
        self._reports.clear()
