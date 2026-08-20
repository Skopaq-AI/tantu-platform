"""Dual router — routes by air_gapped flag, with grounded generation."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, List, Optional

from ..config import settings
from .gemini_client import GeminiClient
from .nemotron_client import NemotronClient
from .grounding import hallucination_guard

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RouteDecision:
    backend: str  # "gemini-er2" | "nemotron-onprem"
    air_gapped: bool
    model: str
    fallback_used: bool


class DualRouter:
    """Routes GENAI calls based on air_gapped flag.

    - air_gapped=True  → always Nemotron on-prem (vLLM/Ollama HTTP path).
    - air_gapped=False → Gemini ER2 if key present, else Nemotron fallback.
    Every generation is grounded (RAG context injected) and guarded.
    """

    def __init__(
        self,
        gemini_client: Optional[GeminiClient] = None,
        nemotron_client: Optional[NemotronClient] = None,
    ):
        self.gemini = gemini_client or GeminiClient()
        self.nemotron = nemotron_client or NemotronClient()

    async def _route_generate(
        self,
        prompt_name: str,
        variables: dict,
        rag_doc_ids: List[str],
        air_gapped: bool,
    ) -> dict:
        rag_context = variables.get("rag_context", "")
        if air_gapped:
            raw = await self.nemotron.generate(prompt_name, variables, rag_doc_ids)
            backend = "nemotron-onprem"
        else:
            if self.gemini.available:
                raw = await self.gemini.generate(prompt_name, variables, rag_doc_ids)
                backend = "gemini-er2"
                # if model indicates fallback (no key/quota), mark
                if "fallback" in raw.get("model", ""):
                    backend = "gemini-er2:fallback"
            else:
                raw = await self.nemotron.generate(prompt_name, variables, rag_doc_ids)
                backend = "nemotron-onprem"

        # grounding guard
        from .prompts import get_prompt

        tpl = get_prompt(prompt_name)
        guarded = hallucination_guard(raw["text"], rag_doc_ids, rag_context, require_citation=tpl.require_citations)
        raw["text"] = guarded
        raw["backend"] = backend
        raw["air_gapped"] = air_gapped
        raw["guarded"] = guarded != raw.get("text", "") or "[needs human check" in guarded or "[ungrounded]" in guarded
        return raw

    async def answer(
        self,
        question: str,
        rag_context: str,
        rag_doc_ids: List[str],
        plant_id: str = "plant-demo-01",
        lang: str = "en",
        air_gapped: bool = False,
        top_k: int = 3,
    ) -> dict:
        variables = {
            "question": question,
            "plant_id": plant_id,
            "rag_context": rag_context or "(no docs retrieved)",
            "lang": lang,
            "top_k": top_k,
        }
        raw = await self._route_generate("ask_v1", variables, rag_doc_ids, air_gapped)
        decision = RouteDecision(
            backend=raw["backend"],
            air_gapped=air_gapped,
            model=raw["model"],
            fallback_used="fallback" in raw["model"],
        )
        return {**raw, "decision": decision}

    async def correlate(
        self,
        events: List[Any],
        rag_context: str,
        rag_doc_ids: List[str],
        lang: str = "en",
        air_gapped: bool = False,
        top_k: int = 5,
    ) -> dict:
        # serialize events (support dict or dataclass)
        def ev_to_dict(e: Any) -> dict:
            if isinstance(e, dict):
                return e
            # dataclass or pydantic
            for attr in ("model_dump", "dict", "__dict__"):
                if hasattr(e, attr):
                    try:
                        v = getattr(e, attr)()
                        if isinstance(v, dict):
                            return v
                    except Exception:
                        pass
            # dataclass fallback
            try:
                from dataclasses import asdict, is_dataclass

                if is_dataclass(e):
                    return asdict(e)  # type: ignore
            except Exception:
                pass
            return {"raw": str(e)}

        events_json = json.dumps([ev_to_dict(e) for e in events], indent=2, default=str)[:6000]
        variables = {
            "events_json": events_json,
            "rag_context": rag_context or "(no docs retrieved)",
            "lang": lang,
            "top_k": top_k,
        }
        raw = await self._route_generate("correlate_v1", variables, rag_doc_ids, air_gapped)
        decision = RouteDecision(
            backend=raw["backend"],
            air_gapped=air_gapped,
            model=raw["model"],
            fallback_used="fallback" in raw["model"],
        )
        return {**raw, "decision": decision}
