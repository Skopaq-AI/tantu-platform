"""Event window policy — pure, auditable, no I/O.

Rule (from spec): escalate if (fault_count >= 2) OR (any confidence >= 0.97)

fault_count = events where defect_class != "none" within the window.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Optional

from .events import DefectEvent, DefectClass


def should_escalate(events: list[DefectEvent], confidence_threshold: float = 0.97) -> bool:
    """Pure function — does window warrant escalation?"""
    if not events:
        return False
    fault_count = sum(1 for e in events if e.defect_class != DefectClass.NONE)
    if fault_count >= 2:
        return True
    if any(e.confidence >= confidence_threshold for e in events):
        return True
    return False


@dataclass
class EventWindowPolicy:
    """Stateful per-plant window with TTL and bounded size.

    Pure in the sense that no I/O; caller owns persistence.
    """

    confidence_threshold: float = 0.97
    max_size: int = 100
    ttl_s: float = 300.0

    # plant_id -> list[(event, ingested_at)]
    _windows: dict[str, list[tuple[DefectEvent, float]]] = field(default_factory=dict)

    def _prune_expired(self, plant_id: str, now: Optional[float] = None) -> None:
        if plant_id not in self._windows:
            return
        now = now if now is not None else time.time()
        lst = self._windows[plant_id]
        # keep only recent
        self._windows[plant_id] = [(e, ts) for e, ts in lst if (now - ts) <= self.ttl_s]
        # bound size — keep most recent max_size
        if len(self._windows[plant_id]) > self.max_size:
            self._windows[plant_id] = self._windows[plant_id][-self.max_size :]

    def ingest(self, event: DefectEvent, now: Optional[float] = None) -> None:
        """Add event to window. Non-fault events (NONE) are still tracked for confidence check."""
        now = now if now is not None else time.time()
        pid = event.plant_id or "plant-demo-01"
        self._prune_expired(pid, now)
        if pid not in self._windows:
            self._windows[pid] = []
        # Only faults and high-confidence contribute to escalation, but we store all for audit
        # Optimization: store all, but should_escalate will filter
        self._windows[pid].append((event, now))
        # prune again after append for size
        if len(self._windows[pid]) > self.max_size:
            self._windows[pid] = self._windows[pid][-self.max_size :]

    def events_for(self, plant_id: str, now: Optional[float] = None) -> list[DefectEvent]:
        self._prune_expired(plant_id, now)
        return [e for e, _ in self._windows.get(plant_id, [])]

    def should_escalate_for(self, plant_id: str, now: Optional[float] = None) -> bool:
        evs = self.events_for(plant_id, now)
        return should_escalate(evs, self.confidence_threshold)

    def should_escalate_global(self) -> bool:
        """Aggregate across plants — true if any plant should escalate."""
        for pid in list(self._windows.keys()):
            if self.should_escalate_for(pid):
                return True
        return False

    def pop_window(self, plant_id: str) -> list[DefectEvent]:
        """Drain and return window for plant — called on escalation."""
        lst = self._windows.get(plant_id, [])
        self._windows[plant_id] = []
        return [e for e, _ in lst]

    def pop_all_escalating(self) -> dict[str, list[DefectEvent]]:
        """Return {plant_id: events} for all plants that should escalate, draining those windows."""
        result: dict[str, list[DefectEvent]] = {}
        for pid in list(self._windows.keys()):
            if should_escalate([e for e, _ in self._windows[pid]], self.confidence_threshold):
                result[pid] = self.pop_window(pid)
        return result

    def clear(self, plant_id: Optional[str] = None) -> None:
        if plant_id is None:
            self._windows.clear()
        else:
            self._windows.pop(plant_id, None)

    def window_sizes(self) -> dict[str, int]:
        return {pid: len(lst) for pid, lst in self._windows.items()}
