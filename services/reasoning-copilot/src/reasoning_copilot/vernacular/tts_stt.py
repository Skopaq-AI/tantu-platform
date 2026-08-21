"""Vernacular TTS/STT — stub with real i18n + real HTTP path when configured.

Real paths (when TTS_URL / STT_URL env are set):
  TTS: POST {TTS_URL}/synthesize  {text, lang, voice} -> {audio_base64, format}
  STT: POST {STT_URL}/transcribe  {audio_base64, lang} -> {text, lang, confidence}

Fallback: deterministic placeholder that still honors hi/ta/te/kn and code-switch,
so the API contract is exercisable without external services.
"""

from __future__ import annotations

import base64
import logging
from typing import Optional

import httpx

from ..config import settings
from .i18n import to_vernacular, SUPPORTED_LANGS

log = logging.getLogger(__name__)


class TtsSttService:
    def __init__(
        self, tts_url: Optional[str] = None, stt_url: Optional[str] = None, timeout_s: float = 6.0
    ):
        self.tts_url = (
            (tts_url or settings.tts_url).rstrip("/") if (tts_url or settings.tts_url) else ""
        )
        self.stt_url = (
            (stt_url or settings.stt_url).rstrip("/") if (stt_url or settings.stt_url) else ""
        )
        self.timeout_s = timeout_s

    # -- TTS -----------------------------------------------------------------

    async def synthesize(self, text: str, lang: str = "en") -> dict:
        if lang not in SUPPORTED_LANGS:
            lang = "en"
        vernacular_text = to_vernacular(text, lang)
        # Try real TTS
        if self.tts_url:
            try:
                async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                    r = await client.post(
                        f"{self.tts_url}/synthesize",
                        json={"text": vernacular_text, "lang": lang, "voice": f"tantu-{lang}"},
                    )
                    if r.status_code == 200:
                        data = r.json()
                        return {
                            "text": vernacular_text,
                            "lang": lang,
                            "audio_base64": data.get("audio_base64", ""),
                            "format": data.get("format", "mp3"),
                            "backend": "external-tts",
                        }
                    log.warning("TTS %s -> %s %s", self.tts_url, r.status_code, r.text[:200])
            except Exception as e:
                log.info("TTS not reachable (%s): %s — stub", self.tts_url, e)

        # Stub: base64 of vernacular text as fake audio
        fake_audio = base64.b64encode(f"[TTS:{lang}]{vernacular_text}".encode()).decode()
        return {
            "text": vernacular_text,
            "lang": lang,
            "audio_base64": fake_audio,
            "format": "wav.stub",
            "backend": "stub-tts",
            "note": "stub audio — base64 of vernacular text; replace TTS_URL for real synthesis",
        }

    # -- STT -----------------------------------------------------------------

    async def transcribe(self, audio_base64: str, lang_hint: str = "en") -> dict:
        # Try real STT
        if self.stt_url:
            try:
                async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                    r = await client.post(
                        f"{self.stt_url}/transcribe",
                        json={"audio_base64": audio_base64, "lang": lang_hint},
                    )
                    if r.status_code == 200:
                        data = r.json()
                        return {
                            "text": data.get("text", ""),
                            "lang": data.get("lang", lang_hint),
                            "confidence": data.get("confidence", 0.92),
                            "backend": "external-stt",
                        }
            except Exception as e:
                log.info("STT not reachable (%s): %s — stub", self.stt_url, e)

        # Stub: try to decode base64 -> if it was our fake TTS, recover text
        text = ""
        try:
            decoded = base64.b64decode(audio_base64).decode(errors="ignore")
            if decoded.startswith("[TTS:"):
                # extract payload after ]
                idx = decoded.find("]")
                text = decoded[idx + 1 :].strip() if idx != -1 else decoded
            elif decoded.strip():
                text = decoded.strip()[:300]
            else:
                text = ""
        except Exception:
            text = ""

        if not text:
            # generic stub transcription per lang
            stubs = {
                "en": "Line 2 pressure high — check valve 3",
                "hi": "Line 2 pressure jaasti — valve 3 check karo",
                "ta": "Line 2 pressure jaasti — valve 3 paarunga",
                "te": "Line 2 pressure ekkuva — valve 3 choodandi",
                "kn": "Line 2 pressure jaasti — valve 3 check maadi",
            }
            text = stubs.get(lang_hint, stubs["en"])

        return {
            "text": to_vernacular(text, lang_hint) if lang_hint != "en" else text,
            "lang": lang_hint,
            "confidence": 0.78,
            "backend": "stub-stt",
            "note": "stub transcription — base64 decode or lang-hint stub; set STT_URL for real STT",
        }

    async def stt_then_translate(self, audio_base64: str, lang_hint: str = "en") -> dict:
        res = await self.transcribe(audio_base64, lang_hint)
        return res
