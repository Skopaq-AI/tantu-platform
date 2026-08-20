"""Application — orchestration policy (when to escalate)."""
from ..domain.events import DefectEvent, CorrelationReport
from ..domain.ports import ReasoningPort

class Orchestrator:
    """Batches derived events; escalates on 2 faults or conf >=0.97. Policy auditable."""
    def __init__(self, reasoning: ReasoningPort):
        self.reasoning = reasoning
        self.window: list[DefectEvent] = []

    def ingest(self, ev: DefectEvent) -> None:
        if ev.defect_class.value != "none":
            self.window.append(ev)

    def should_escalate(self) -> bool:
        return len(self.window) >= 2 or any(e.confidence >= 0.97 for e in self.window)

    async def maybe_escalate(self) -> CorrelationReport | None:
        if not self.should_escalate():
            return None
        report = await self.reasoning.correlate(self.window)
        self.window.clear()
        return report
