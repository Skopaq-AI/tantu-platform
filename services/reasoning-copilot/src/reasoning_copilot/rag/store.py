"""RAG store — Qdrant (qdrant-client) with real cosine search + chunking + citations.

Real path: QdrantClient(url=QDRANT_URL, api_key=...) → persistent collection.
Fallback: in-memory dict with Embedder cosine search (no server needed for tests/CI).

Documents are chunked before embedding. Each chunk is a point with payload {text, metadata}.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from ..config import settings
from .chunker import chunk_document
from .embeddings import Embedder

log = logging.getLogger(__name__)


@dataclass
class Document:
    id: str
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class SearchHit:
    doc_id: str
    text: str
    score: float
    metadata: dict
    vector: Optional[np.ndarray] = None


class RagStore:
    def __init__(
        self,
        collection: Optional[str] = None,
        embedder: Optional[Embedder] = None,
        qdrant_url: Optional[str] = None,
    ):
        self.collection = collection or settings.qdrant_collection
        self.embedder = embedder or Embedder(dim=settings.embedding_dim)
        self.qdrant_url = qdrant_url or settings.qdrant_url
        self._client = None
        self._use_qdrant = False
        # in-memory fallback
        self._mem_points: List[dict] = []  # {id, doc_id, text, metadata, vector}
        self._try_qdrant()

    def _try_qdrant(self):
        try:
            from qdrant_client import QdrantClient  # type: ignore
            from qdrant_client.models import Distance, VectorParams  # type: ignore

            url = self.qdrant_url
            api_key = settings.qdrant_api_key or None
            self._client = QdrantClient(url=url, api_key=api_key, timeout=5)
            # ensure collection
            try:
                cols = [c.name for c in self._client.get_collections().collections]
            except Exception:
                cols = []
            if self.collection not in cols:
                self._client.create_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(size=self.embedder.dim, distance=Distance.COSINE),
                )
                log.info(
                    "RagStore: created Qdrant collection %s dim=%s at %s",
                    self.collection,
                    self.embedder.dim,
                    url,
                )
            else:
                log.info("RagStore: using Qdrant collection %s at %s", self.collection, url)
            self._use_qdrant = True
        except Exception as e:
            log.info("RagStore: Qdrant not available (%s) — in-memory fallback", e)
            self._client = None
            self._use_qdrant = False

    # -- ingest ---------------------------------------------------------------

    def add(self, doc: Document) -> int:
        """Add doc chunked + embedded. Returns chunk count."""
        chunks = chunk_document(
            doc.id,
            doc.text,
            doc.metadata,
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap,
        )
        if not chunks:
            return 0
        texts = [c["text"] for c in chunks]
        vecs = self.embedder.embed(texts)

        if self._use_qdrant and self._client is not None:
            try:
                from qdrant_client.models import PointStruct  # type: ignore

                points = []
                for ch, vec in zip(chunks, vecs):
                    pid = str(uuid.uuid5(uuid.NAMESPACE_DNS, ch["id"]))
                    points.append(
                        PointStruct(
                            id=pid,
                            vector=vec.tolist(),
                            payload={
                                "doc_id": ch["id"],
                                "parent_id": doc.id,
                                "text": ch["text"],
                                "metadata": ch["metadata"],
                            },
                        )
                    )
                self._client.upsert(collection_name=self.collection, points=points)
                return len(points)
            except Exception as e:
                log.warning("Qdrant upsert failed (%s) — falling back to mem", e)
                self._use_qdrant = False

        # in-memory
        for ch, vec in zip(chunks, vecs):
            self._mem_points.append(
                {
                    "id": ch["id"],
                    "doc_id": ch["id"],
                    "parent_id": doc.id,
                    "text": ch["text"],
                    "metadata": ch["metadata"],
                    "vector": vec,
                }
            )
        return len(chunks)

    def add_many(self, docs: List[Document]) -> int:
        total = 0
        for d in docs:
            total += self.add(d)
        return total

    # -- search ---------------------------------------------------------------

    def search(self, query: str, top_k: int = 3, score_threshold: float = 0.05) -> List[SearchHit]:
        if not query.strip():
            return []
        qvec = self.embedder.embed_one(query)

        if self._use_qdrant and self._client is not None:
            try:
                res = self._client.search(
                    collection_name=self.collection,
                    query_vector=qvec.tolist(),
                    limit=top_k,
                    score_threshold=score_threshold if score_threshold > 0 else None,
                )
                hits = []
                for p in res:
                    payload = p.payload or {}
                    hits.append(
                        SearchHit(
                            doc_id=payload.get("doc_id", str(p.id)),
                            text=payload.get("text", ""),
                            score=float(p.score),
                            metadata=payload.get("metadata", {}),
                        )
                    )
                if hits:
                    return hits
            except Exception as e:
                log.warning("Qdrant search failed (%s) — mem fallback", e)
                self._use_qdrant = False

        # in-memory cosine search
        if not self._mem_points:
            return []
        scored: List[tuple[float, dict]] = []
        qn = np.linalg.norm(qvec)
        for pt in self._mem_points:
            v = pt["vector"]
            denom = qn * np.linalg.norm(v)
            score = float(np.dot(qvec, v) / denom) if denom else 0.0
            # small lexical boost for exact token overlap
            q_tokens = set(query.lower().split())
            d_tokens = set(pt["text"].lower().split())
            if q_tokens & d_tokens:
                score += 0.08 * len(q_tokens & d_tokens) / max(1, len(q_tokens))
            if score >= score_threshold:
                scored.append((score, pt))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            SearchHit(doc_id=pt["doc_id"], text=pt["text"], score=s, metadata=pt["metadata"])
            for s, pt in scored[:top_k]
        ]

    # -- maintenance ----------------------------------------------------------

    def count(self) -> int:
        if self._use_qdrant and self._client is not None:
            try:
                info = self._client.get_collection(self.collection)
                return int(info.points_count or 0)  # type: ignore
            except Exception:
                pass
        return len(self._mem_points)

    def clear(self):
        if self._use_qdrant and self._client is not None:
            try:
                self._client.delete_collection(self.collection)
                # recreate
                from qdrant_client.models import Distance, VectorParams  # type: ignore

                self._client.create_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(size=self.embedder.dim, distance=Distance.COSINE),
                )
            except Exception:
                pass
        self._mem_points.clear()

    @property
    def backend(self) -> str:
        return "qdrant" if self._use_qdrant else "memory"
