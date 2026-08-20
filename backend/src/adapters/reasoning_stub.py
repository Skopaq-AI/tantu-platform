"""Infra — stub for dual GENAI (swap to real Gemini/vLLM)."""
import random
from ..domain.events import DefectEvent, CorrelationReport

GEMINI_IN, GEMINI_OUT = 2.00, 10.00  # $/M tokens — from Business Plan

class DualStub:
    async def correlate(self, events: list[DefectEvent]) -> CorrelationReport:
        n = len([e for e in events if e.defect_class.value!="none"])
        stations = sorted({e.station_id for e in events})
        summary = f"{n} fault(s) across {len(stations)} station(s): {', '.join(stations[:3])}. Recommend valve 3 check (RAG grounded stub)."
        ti, to = random.randint(220,420), random.randint(120,260)
        cost = ti/1e6*GEMINI_IN + to/1e6*GEMINI_OUT
        return CorrelationReport(summary=summary, contributing=stations, confidence=round(random.uniform(0.72,0.91),2), tokens_in=ti, tokens_out=to, cost_usd=cost)
    async def answer(self, question: str, context: dict) -> str:
        return f"[stub] '{question}' → check valve 3, vibration up 12% (grounded from tag map)."
