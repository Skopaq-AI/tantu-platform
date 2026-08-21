"""Citation helpers — build grounded context windows."""

from __future__ import annotations

from typing import List


def format_context(hits, max_chars: int = 4000) -> str:
    """Turn SearchHits into LLM context string with [doc:id] markers."""
    parts: List[str] = []
    total = 0
    for h in hits:
        block = f"[doc:{h.doc_id}] {h.text.strip()} (score={h.score:.3f}, meta={h.metadata})"
        if total + len(block) > max_chars:
            break
        parts.append(block)
        total += len(block)
    return (
        "\n---\n".join(parts) if parts else "(no relevant docs — answer must say needs human check)"
    )


def build_citations(hits) -> List[dict]:
    return [
        {
            "doc_id": h.doc_id,
            "score": round(float(h.score), 4),
            "text_snippet": h.text[:200],
            "metadata": h.metadata,
        }
        for h in hits
    ]
