"""Chunking — split docs for embedding."""

from __future__ import annotations

from typing import List


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> List[str]:
    """Character-based chunking with overlap.

    Keeps sentences intact where possible; falls back to hard window.
    """
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text.strip()]

    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        # try to break at sentence boundary within last 20%
        if end < n:
            window = text[max(start, end - chunk_size // 5) : end]
            # prefer ". " or "\n"
            for sep in [". ", "\n", "; "]:
                idx = window.rfind(sep)
                if idx != -1:
                    end = max(start, end - chunk_size // 5) + idx + len(sep)
                    break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = end - overlap
        if start < 0:
            start = 0
    return chunks


def chunk_document(
    doc_id: str, text: str, metadata: dict, chunk_size: int = 800, overlap: int = 120
) -> List[dict]:
    pieces = chunk_text(text, chunk_size, overlap)
    out = []
    for i, p in enumerate(pieces):
        out.append(
            {
                "id": f"{doc_id}#chunk{i}",
                "text": p,
                "metadata": {
                    **metadata,
                    "parent_id": doc_id,
                    "chunk_index": i,
                    "chunk_count": len(pieces),
                },
            }
        )
    return out
