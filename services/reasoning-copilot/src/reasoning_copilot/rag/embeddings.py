"""Embeddings — sentence-transformers with real cosine fallback.

Real path: sentence-transformers (e.g. all-MiniLM-L6-v2, 384-dim).
Stub fallback: deterministic hash-embedding with L2 norm + real cosine similarity,
so RAG grounding tests pass without downloading a 90MB model.
"""

from __future__ import annotations

import hashlib
import logging
from typing import List

import numpy as np

log = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer  # type: ignore

    _HAS_ST = True
except Exception:  # pragma: no cover
    _HAS_ST = False


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _hash_embed_one(text: str, dim: int = 384) -> np.ndarray:
    """Deterministic hash embedding: token-hash -> vector, L2 normalized."""
    vec = np.zeros(dim, dtype=np.float32)
    tokens = text.lower().split()
    if not tokens:
        tokens = [text.lower()[:32]]
    for tok in tokens:
        # hash token to dim buckets with sign
        h = int(hashlib.sha256(tok.encode()).hexdigest()[:8], 16)
        idx = h % dim
        sign = 1.0 if (h >> 16) % 2 == 0 else -1.0
        # tf-like weight by length
        w = 1.0 + 0.1 * min(len(tok), 10)
        vec[idx] += sign * w
    # add char bigram signal for OOV robustness
    for i in range(len(text) - 1):
        bg = text[i : i + 2].lower()
        h = int(hashlib.md5(bg.encode()).hexdigest()[:8], 16)
        idx = h % dim
        vec[idx] += 0.15
    n = np.linalg.norm(vec)
    if n > 0:
        vec /= n
    return vec


class Embedder:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", dim: int = 384):
        self.model_name = model_name
        self.dim = dim
        self._model = None
        self._use_st = False
        if _HAS_ST:
            try:
                # lazy load only if sentence-transformers import succeeded
                # do not auto-download in __init__ if offline; try and fallback
                self._model = SentenceTransformer(model_name)
                self._use_st = True
                # infer dim
                try:
                    self.dim = self._model.get_sentence_embedding_dimension()  # type: ignore
                except Exception:
                    pass
                log.info("Embedder: loaded %s dim=%s", model_name, self.dim)
            except Exception as e:
                log.warning("Embedder ST load failed (%s) — using hash embed dim=%s", e, dim)
                self._model = None
                self._use_st = False
        else:
            log.info("Embedder: sentence-transformers not installed — hash embed dim=%s", dim)

    @property
    def is_transformer(self) -> bool:
        return self._use_st

    def embed(self, texts: List[str]) -> np.ndarray:
        """Return (n, dim) float32 matrix, L2-normalized."""
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        if self._use_st and self._model is not None:
            try:
                vecs = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)  # type: ignore
                arr = np.asarray(vecs, dtype=np.float32)
                return arr
            except Exception as e:
                log.warning("ST encode failed (%s) — fallback hash", e)
        # fallback
        mat = np.vstack([_hash_embed_one(t, self.dim) for t in texts])
        return mat.astype(np.float32)

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed([text])[0]

    def similarity(self, query: str, docs: List[str]) -> List[float]:
        qv = self.embed_one(query)
        dm = self.embed(docs)
        return [cosine_similarity(qv, dm[i]) for i in range(len(docs))]
