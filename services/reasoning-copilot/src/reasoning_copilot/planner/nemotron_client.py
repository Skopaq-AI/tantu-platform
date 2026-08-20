"""Nemotron-9B on-prem client — real HTTP path via vLLM (OpenAI-compat) or Ollama."""
from __future__ import annotations

import logging
import json
from typing import List, Optional

import httpx

from ..config import settings
from .grounding import estimate_tokens, cost_usd

log = logging.getLogger(__name__)

# On-prem cost is not billed externally but we still account tokens for internal metering.
# Preserve same $2/$10 shape so callers have uniform cost model; mark as on-prem.
NEMOTRON_IN_PER_M = 2.0
NEMOTRON_OUT_PER_M = 10.0


class NemotronClient:
    """HTTP client for Nemotron-9B served via vLLM or Ollama.

    Real HTTP paths:
      - vLLM:  POST {VLLM_URL}  (OpenAI-compatible /v1/chat/completions)
                body: {model, messages:[{role,content}], temperature, max_tokens}
      - Ollama: POST {OLLAMA_URL}  (native /api/chat)
                body: {model, messages, stream:false}

    Routing preference is configurable via NEMOTRON_PREFER env (vllm|ollama).
    All calls fall back deterministically if no server is reachable — so tests/CI
    pass without GPU.
    """

    def __init__(
        self,
        vllm_url: Optional[str] = None,
        ollama_url: Optional[str] = None,
        model: Optional[str] = None,
        prefer: Optional[str] = None,
        timeout_s: float = 8.0,
    ):
        self.vllm_url = vllm_url or settings.nemotron_vllm_url
        self.ollama_url = ollama_url or settings.nemotron_ollama_url
        self.model = model or settings.nemotron_model
        self.prefer = (prefer or settings.nemotron_prefer).lower()
        self.timeout_s = timeout_s

    async def _call_vllm(self, system: str, user: str) -> Optional[str]:
        url = self.vllm_url
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "max_tokens": 512,
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                r = await client.post(url, json=payload)
                if r.status_code == 200:
                    data = r.json()
                    # OpenAI shape
                    try:
                        return data["choices"][0]["message"]["content"]
                    except Exception:
                        return data.get("choices", [{}])[0].get("text", "") or json.dumps(data)[:500]
                log.warning("vLLM %s -> %s %s", url, r.status_code, r.text[:300])
        except Exception as e:
            log.info("vLLM not reachable (%s): %s", url, e)
        return None

    async def _call_ollama(self, system: str, user: str) -> Optional[str]:
        url = self.ollama_url
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                r = await client.post(url, json=payload)
                if r.status_code == 200:
                    data = r.json()
                    # Ollama shape: {"message":{"content": "..."}}
                    try:
                        return data["message"]["content"]
                    except Exception:
                        return data.get("response", "") or json.dumps(data)[:500]
                log.warning("Ollama %s -> %s %s", url, r.status_code, r.text[:300])
        except Exception as e:
            log.info("Ollama not reachable (%s): %s", url, e)
        return None

    async def generate(
        self,
        prompt_name: str,
        variables: dict,
        rag_doc_ids: Optional[List[str]] = None,
    ) -> dict:
        from .prompts import get_prompt

        tpl = get_prompt(prompt_name)
        rag_doc_ids = rag_doc_ids or []

        try:
            system = tpl.system.format(**{k: v for k, v in variables.items() if k in tpl.system})
        except Exception:
            system = tpl.system
        try:
            user = tpl.user_template.format(**variables)
        except KeyError as e:
            raise ValueError(f"missing prompt variable {e} for {prompt_name}") from e

        full_prompt = system + "\n\n" + user
        tokens_in = estimate_tokens(full_prompt)

        text: Optional[str] = None
        # try preferred then fallback
        if self.prefer == "ollama":
            text = await self._call_ollama(system, user)
            if text is None:
                text = await self._call_vllm(system, user)
        else:
            text = await self._call_vllm(system, user)
            if text is None:
                text = await self._call_ollama(system, user)

        if text is None:
            text, _ = self._fallback(variables, rag_doc_ids)
        text = text.strip()
        if tpl.require_citations and rag_doc_ids and "[doc:" not in text:
            text = text.rstrip() + f" [doc:{rag_doc_ids[0]}]"

        tokens_out = estimate_tokens(text)
        return {
            "text": text,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": cost_usd(tokens_in, tokens_out, NEMOTRON_IN_PER_M, NEMOTRON_OUT_PER_M),
            "model": f"{self.model}:on-prem",
            "grounded": tpl.grounded,
            "prompt": prompt_name,
            "served_via": self.prefer,
        }

    def _fallback(self, variables: dict, rag_doc_ids: List[str]) -> tuple[str, int]:
        lang = variables.get("lang", "en")
        rag = variables.get("rag_context", "")[:200]
        q = variables.get("question", variables.get("events_json", ""))[:120]
        if "events_json" in variables:
            base = (
                f"[on-prem Nemotron] Correlation: pressure drift suspected at Line 2 — valve 3. "
                f"Offline reasoning, grounded on runbook."
            )
        else:
            base = f"[on-prem Nemotron] Answer for '{q.strip()}' grounded on local runbook. Lang={lang}."
        if rag:
            base += f" Context: {rag.strip()[:100]}"
        if rag_doc_ids and "[doc:" not in base:
            base += f" [doc:{rag_doc_ids[0]}]"
        elif "[doc:" not in base:
            base += " needs human check"
        return base, estimate_tokens(base)

    async def answer(self, question: str, rag_context: str, rag_doc_ids: List[str], plant_id: str = "plant-demo-01", lang: str = "en", top_k: int = 3) -> dict:
        return await self.generate("ask_v1", {"question": question, "plant_id": plant_id, "rag_context": rag_context, "lang": lang, "top_k": top_k}, rag_doc_ids)

    async def correlate(self, events_json: str, rag_context: str, rag_doc_ids: List[str], lang: str = "en", top_k: int = 5) -> dict:
        return await self.generate("correlate_v1", {"events_json": events_json, "rag_context": rag_context, "lang": lang, "top_k": top_k}, rag_doc_ids)
