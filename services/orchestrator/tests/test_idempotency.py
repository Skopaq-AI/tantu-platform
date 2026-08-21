"""Tests — idempotency + orchestrator service deduplication."""

import pytest

from orchestrator.domain.events import DefectEvent, DefectClass, Track
from orchestrator.domain.policies import EventWindowPolicy
from orchestrator.application.orchestrator_service import OrchestratorService
from orchestrator.infra.idempotency import IdempotencyStore


def _ev(event_id="evt-1", defect="pressure_drift", conf=0.5, plant_id="plant-a", station="s1"):
    klass = DefectClass(defect)
    return DefectEvent(
        station_id=station,
        track=Track.LINE,
        defect_class=klass,
        confidence=conf,
        latency_ms=22.0,
        plant_id=plant_id,
        event_id=event_id,
    )


@pytest.mark.asyncio
async def test_idempotency_store_put_and_get():
    store = IdempotencyStore()
    assert await store.get("k1") is None
    ok = await store.put("k1", {"x": 1})
    assert ok is True
    # duplicate put fails
    ok2 = await store.put("k1", {"x": 2})
    assert ok2 is False
    # get returns first value
    v = await store.get("k1")
    assert v == {"x": 1}
    assert await store.exists("k1") is True
    assert await store.exists("nope") is False


@pytest.mark.asyncio
async def test_orchestrator_idempotent_ingest_no_escalate():
    policy = EventWindowPolicy(confidence_threshold=0.97, max_size=10, ttl_s=60)
    _svc = OrchestratorService(policy=policy)  # instantiated to warm singleton, not directly used
    # Ensure clean store (global singleton is used by service — we patch by clearing)
    from orchestrator.infra import idempotency as idem_mod

    # Replace global store with fresh for isolation
    fresh = IdempotencyStore()
    idem_mod.idempotency_store = fresh
    svc_dup = OrchestratorService(
        policy=EventWindowPolicy(confidence_threshold=0.97, max_size=10, ttl_s=60)
    )
    # inject fresh store via monkeypatch of module attr (service reads global at call time)
    # Provide single-fault event — should NOT escalate, and duplicate should be deduped
    ev = _ev(event_id="dup-1", defect="pressure_drift", conf=0.5)
    escalated, report = await svc_dup.ingest(ev)
    assert escalated is False
    assert report is None
    # second ingest same event_id — should return same result via idempotency
    escalated2, report2 = await svc_dup.ingest(ev)
    assert escalated2 is False
    assert report2 is None
    # window should still have only 1 event (not duplicated)
    assert svc_dup.policy.window_sizes()["plant-a"] == 1


@pytest.mark.asyncio
async def test_orchestrator_escalation_and_idempotency():
    from orchestrator.infra import idempotency as idem_mod

    fresh = IdempotencyStore()
    idem_mod.idempotency_store = fresh
    policy = EventWindowPolicy(confidence_threshold=0.97, max_size=10, ttl_s=60)
    svc = OrchestratorService(policy=policy)

    ev1 = _ev(event_id="e1", defect="pressure_drift", conf=0.5, station="s1")
    ev2 = _ev(event_id="e2", defect="vib_high", conf=0.5, station="s2")

    # First ingest — no escalate yet
    esc1, rep1 = await svc.ingest(ev1)
    assert esc1 is False
    # Second ingest — triggers 2 faults → escalate
    esc2, rep2 = await svc.ingest(ev2)
    assert esc2 is True
    assert rep2 is not None
    assert rep2.plant_id == "plant-a"
    assert len(rep2.contributing) == 2
    # Window cleared after escalation
    assert svc.policy.window_sizes().get("plant-a", 0) == 0

    # Duplicate of e2 → should return escalated True with same report (idempotent)
    esc_dup, rep_dup = await svc.ingest(ev2)
    assert esc_dup is True
    assert rep_dup is not None
    assert rep_dup.id == rep2.id

    # New event after clear — single fault again → no escalate
    ev3 = _ev(event_id="e3", defect="pressure_drift", conf=0.5, station="s3")
    esc3, rep3 = await svc.ingest(ev3)
    assert esc3 is False
