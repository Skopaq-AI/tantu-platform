"""Ports — hexagonal."""
from typing import Protocol, List
from .events import DefectEvent, TelemetryReading, CorrelationReport

class EventPublisher(Protocol):
    async def publish(self, event: DefectEvent) -> None: ...

class ReasoningPort(Protocol):
    async def correlate(self, events: List[DefectEvent]) -> CorrelationReport: ...
    async def answer(self, question: str, context: dict) -> str: ...
