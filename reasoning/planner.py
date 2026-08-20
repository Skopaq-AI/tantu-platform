"""Dual planner — routes by air_gapped flag."""
from backend.src.domain.events import DefectEvent, CorrelationReport
from backend.src.adapters.reasoning_stub import DualStub
# Real paths (commented, production):
# from google import genai  # Gemini ER2 via genai.Client(api_key=...)
# from vllm import LLM  # Nemotron-9B on-prem

class DualPlanner:
    def __init__(self, air_gapped=False):
        self.air_gapped = air_gapped
        self.stub = DualStub()
    async def correlate(self, events: list[DefectEvent]) -> CorrelationReport:
        # if self.air_gapped: return await self._vllm_correlate(events)
        # else: return await self._gemini_correlate(events)
        return await self.stub.correlate(events)
    async def answer(self, q: str, ctx: dict) -> str:
        return await self.stub.answer(q, ctx)
