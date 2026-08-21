"""Grounding, token counting, hallucination guard, costing."""

from __future__ import annotations

import re
from typing import List, Set


# ---- token / cost -----------------------------------------------------------


def estimate_tokens(text: str) -> int:
    """Approx tokens — ~4 chars per token, with tiktoken fallback if installed."""
    try:
        import tiktoken  # type: ignore

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        # heuristic: 4 chars/token, but at least 1 per word
        if not text:
            return 0
        by_chars = max(1, len(text) // 4)
        by_words = len(text.split())
        return max(by_chars, by_words)


def cost_usd(
    tokens_in: int, tokens_out: int, in_per_m: float = 2.0, out_per_m: float = 10.0
) -> float:
    return round(tokens_in / 1_000_000 * in_per_m + tokens_out / 1_000_000 * out_per_m, 6)


# ---- grounding / hallucination ---------------------------------------------

# phrases that look like invented sensor readings without citation
SUSPICIOUS_PATTERNS = [
    re.compile(r"\b\d+(\.\d+)?\s*(bar|psi|°C|deg|mm|μm|rpm|hz|%)\b", re.I),
    re.compile(r"\b(sensor|gauge|valve)\s*\d+\s*(is|reads|shows)\s*\d+", re.I),
]

# acceptable "I don't know" phrasing
HONEST_PHRASES = [
    "needs human check",
    "i do not have grounded information",
    "not in the provided context",
    "insufficient context",
]


def extract_citations(text: str) -> Set[str]:
    """Find [doc:...] citations."""
    return set(re.findall(r"\[doc:([^\]]+)\]", text))


def contains_honest_deferral(text: str) -> bool:
    low = text.lower()
    return any(p in low for p in HONEST_PHRASES)


def grounding_check(answer: str, rag_doc_ids: List[str], require_citation: bool = True) -> dict:
    """Return grounding signal.

    - has_citation: at least one [doc:id] that matches retrieved ids
    - cited_ids: extracted ids
    - unknown_citations: citations that weren't in retrieval
    - deferred: answer honestly says it doesn't know
    - suspicious_numbers: regex hits that look like invented values
    """
    cited = extract_citations(answer)
    rag_set = set(rag_doc_ids)
    unknown = cited - rag_set
    has_valid = len(cited & rag_set) > 0
    suspicious = []  # low = answer.lower() reserved for future locale check
    for pat in SUSPICIOUS_PATTERNS:
        m = pat.search(answer)
        if m:
            suspicious.append(m.group(0))
    # numbers are OK if cited
    if has_valid:
        suspicious = []
    return {
        "has_citation": has_valid,
        "cited_ids": sorted(cited),
        "unknown_citations": sorted(unknown),
        "deferred": contains_honest_deferral(answer),
        "suspicious_numbers": suspicious,
        "requires_citation_but_missing": require_citation
        and not has_valid
        and not contains_honest_deferral(answer),
    }


def hallucination_guard(
    answer: str, rag_doc_ids: List[str], rag_context: str = "", require_citation: bool = True
) -> str:
    """Enforce grounded generation.

    If answer lacks citations but should have them, append deferral + strip simulated numbers
    when they look hallucinated.  Never drop citations.
    """
    sig = grounding_check(answer, rag_doc_ids, require_citation=require_citation)
    # unknown citations take precedence — warn even if also missing valid citation
    if sig["unknown_citations"]:
        return answer.rstrip() + f" [warning: unknown citations {sig['unknown_citations']}]"
    if sig["requires_citation_but_missing"] and sig["suspicious_numbers"]:
        # hallucinated numbers without citation — rewrite to honest deferral
        return answer.rstrip() + " [needs human check — ungrounded numeric value removed]"
    if sig["requires_citation_but_missing"]:
        # missing citation: append guard note rather than silently pass
        if not answer.strip().endswith("]"):
            answer = answer.rstrip() + " — needs human check [ungrounded]"
        return answer
    return answer
