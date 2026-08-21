"""Vernacular exports."""

from .i18n import to_vernacular, code_switch, SUPPORTED_LANGS, TRANSLATIONS, detect_lang
from .tts_stt import TtsSttService

__all__ = [
    "to_vernacular",
    "code_switch",
    "SUPPORTED_LANGS",
    "TRANSLATIONS",
    "detect_lang",
    "TtsSttService",
]
