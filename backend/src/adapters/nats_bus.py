"""Infra — NATS bus stub (swap to real NATS in compose)."""
import asyncio
from ..domain.events import DefectEvent

class NatsBus:
    def __init__(self): self._subs = []
    async def publish(self, event: DefectEvent) -> None:
        for cb in self._subs: await cb(event)
    def subscribe(self, cb): self._subs.append(cb)
