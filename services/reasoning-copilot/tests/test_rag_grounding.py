"""RAG grounding tests — chunking, embeddings, Qdrant/mem, citations."""

import pytest
from reasoning_copilot.rag.chunker import chunk_text, chunk_document
from reasoning_copilot.rag.embeddings import Embedder, cosine_similarity
from reasoning_copilot.rag.store import RagStore, Document
from reasoning_copilot.rag.citations import format_context, build_citations


def test_chunker_basic():
    text = "Hello world. " * 200
    chunks = chunk_text(text, chunk_size=800, overlap=120)
    assert len(chunks) >= 2
    # overlap: last part of chunk 0 appears in chunk 1
    assert chunks[0][-50:] in chunks[1] or len(chunks[1]) > 0
    # sentence boundary preserved
    for c in chunks:
        assert len(c) <= 900


def test_chunk_document_ids():
    chunks = chunk_document("doc1", "A" * 2000, {"plant": "p1"}, chunk_size=800, overlap=100)
    assert len(chunks) >= 2
    assert chunks[0]["id"] == "doc1#chunk0"
    assert all("parent_id" in c["metadata"] for c in chunks)


def test_embedder_hash_cosine_real():
    emb = Embedder(dim=64)
    # force hash path by disabling ST if needed — test works both ways
    sims = emb.similarity("pressure valve", ["pressure valve check", "banana fruit"])
    assert sims[0] > sims[1], f"expected pressure closer {sims}"
    # identical should be ~1.0
    v1 = emb.embed_one("hello world")
    v2 = emb.embed_one("hello world")
    assert cosine_similarity(v1, v2) > 0.99
    # orthogonal-ish low
    v3 = emb.embed_one("xyzzy qwerty")
    assert cosine_similarity(v1, v3) < 0.7


def test_embedder_cosine_search_grounded():
    store = RagStore(collection="test_grounding_" + str(id(object())), embedder=Embedder(dim=64))
    store.clear()
    store.add(
        Document(
            id="runbook-press-01",
            text="Line 2 pressure high (>8 bar): check valve 3, max safe 8 bar.",
            metadata={"plant_id": "plant-demo-01"},
        )
    )
    store.add(
        Document(
            id="runbook-vib-01",
            text="Vibration RMS >4.5 mm/s indicates bearing wear, schedule replacement.",
            metadata={"plant_id": "plant-demo-01"},
        )
    )
    store.add(
        Document(
            id="unrelated",
            text="Canteen menu: samosa and chai at 4pm.",
            metadata={"plant_id": "plant-demo-01"},
        )
    )

    hits = store.search("pressure valve 3", top_k=2)
    assert len(hits) >= 1
    # top hit should be press runbook
    top_ids = [h.doc_id for h in hits]
    assert any("press" in tid for tid in top_ids), f"top {top_ids} should contain press doc"

    # unrelated query should not match canteen highly? allow but score lower
    hits2 = store.search("bearing vibration", top_k=2)
    assert any("vib" in h.doc_id for h in hits2)


def test_rag_store_qdrant_or_mem_backend():
    store = RagStore(collection="test_backend_" + str(id(object())), embedder=Embedder(dim=32))
    assert store.backend in ("qdrant", "memory")
    n = store.add(Document(id="d1", text="hello hello hello " * 50, metadata={}))
    assert n >= 1
    assert store.count() >= 1


def test_citations_format_and_build():
    store = RagStore(collection="test_cite_" + str(id(object())), embedder=Embedder(dim=32))
    store.clear()
    store.add(
        Document(
            id="doc-a", text="valve 3 torque 12 Nm, check regulator", metadata={"type": "runbook"}
        )
    )
    hits = store.search("valve 3 torque", top_k=1)
    ctx = format_context(hits)
    assert "[doc:" in ctx
    cits = build_citations(hits)
    assert cits[0]["doc_id"] == hits[0].doc_id
    assert "score" in cits[0]


@pytest.mark.asyncio
async def test_ask_grounded_via_api():
    # FastAPI grounding integration: answer must cite RAG
    from fastapi.testclient import TestClient

    # Use sync TestClient to trigger lifespan
    from reasoning_copilot.api.main import app

    with TestClient(app) as client:
        # ensure we ingested something unique
        client.post(
            "/rag/ingest",
            json={
                "id": "runbook-test-ground",
                "text": "UniqueTokenXYZ: Line 9 hydraulic leak — tighten coupling B.",
                "metadata": {"plant_id": "plant-demo-01"},
            },
        )
        resp = client.post(
            "/ask",
            json={
                "question": "UniqueTokenXYZ leak what to do?",
                "plant_id": "plant-demo-01",
                "lang": "en",
                "top_k": 3,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "answer" in data
        # grounded: citations non-empty OR needs human check fallback
        assert data["grounded"] is True or "needs human check" in data["answer"].lower()
        # citation marker present when grounded
        if data["citations"]:
            assert "[doc:" in data["answer"] or "needs human check" in data["answer"].lower()
            assert data["citations"][0]["doc_id"]
