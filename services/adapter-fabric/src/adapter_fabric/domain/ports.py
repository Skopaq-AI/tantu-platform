"""Ports — hexagonal boundaries."""

from __future__ import annotations

from typing import AsyncIterator, Protocol, List, Optional

from .events import DefectEvent, NormalizedReading, AdapterHealth


class AdapterPort(Protocol):
    """Inbound adapter contract — all protocol adapters implement this."""

    @property
    def adapter_id(self) -> str: ...

    @property
    def protocol(self) -> str: ...

    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def health(self) -> AdapterHealth: ...
    def readings(self) -> AsyncIterator[NormalizedReading]: ...

    # For polling adapters
    async def poll_once(self) -> List[NormalizedReading]: ...


class EventPublisher(Protocol):
    async def publish(self, event: DefectEvent) -> None: ...
    async def publish_reading(self, reading: NormalizedReading) -> None: ...


class ReadingSink(Protocol):
    async def emit(self, reading: NormalizedReading) -> None: ...


class DefectDetector(Protocol):
    """Pure function: readings → optional defect."""

    def detect(self, reading: NormalizedReading) -> Optional[DefectEvent]: ...
