"""Vernacular — hi/ta/te/kn, code-switch, TTS/STT stub."""
VERNACULAR = {
  "en": "Line 2 pressure high — check valve 3",
  "hi": "Line 2 pressure jaasti — valve 3 check karo",
  "ta": "Line 2 pressure jaasti — valve 3 paarunga",
  "te": "Line 2 pressure ekkuva — valve 3 choodandi",
  "kn": "Line 2 pressure jaasti — valve 3 check maadi",
}
def to_vernacular(text: str, lang="ta") -> str: return VERNACULAR.get(lang, VERNACULAR["en"])
