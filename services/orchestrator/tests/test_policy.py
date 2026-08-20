"""Tests — event window policy (2 faults OR conf≥0.97 → escalate)."""
import time
import pytest

from orchestrator.domain.events import DefectEvent, DefectClass, Track, make_event
from orchestrator.domain.policies import should_escalate, EventWindowPolicy


def ev(defect="pressure_drift", conf=0.9, plant_id="plant-a", station="s1"):
    klass = DefectClass(defect) if defect in DefectClass._value2member_map_ else DefectClass.NONE
    return DefectEvent(
        station_id=station,
        track=Track.LINE,
        defect_class=klass,
        confidence=conf,
        latency_ms=22.0,
        plant_id=plant_id,
        event_id=f"{station}-{defect}-{conf}-{time.time_ns()}",
    )


def test_should_escalate_no_events_false():
    assert not should_escalate([])

def test_should_escalate_single_fault_below_threshold_false():
    assert not should_escalate([ev("pressure_drift", 0.9)])

def test_should_escalate_two_faults_true():
    assert should_escalate([ev("pressure_drift", 0.5), ev("vib_high", 0.5)])

def test_should_escalate_single_high_conf_true():
    assert should_escalate([ev("pressure_drift", 0.97)])
    assert should_escalate([ev("none", 0.97)])
    assert not should_escalate([ev("pressure_drift", 0.969)])

def test_should_escalate_custom_threshold():
    assert should_escalate([ev("pressure_drift", 0.85)], confidence_threshold=0.85)
    assert not should_escalate([ev("pressure_drift", 0.84)], confidence_threshold=0.85)

def test_none_defect_not_counted_as_fault_but_conf_still_matters():
    # 1 none @0.5 + 1 fault @0.5 → only 1 fault → no escalate
    assert not should_escalate([ev("none", 0.5), ev("pressure_drift", 0.5)])
    # none @0.99 → escalates via confidence even though not a fault
    assert should_escalate([ev("none", 0.99)])

def test_policy_per_plant_isolation():
    policy = EventWindowPolicy(confidence_threshold=0.97, max_size=10, ttl_s=60)
    policy.ingest(ev("pressure_drift", 0.5, plant_id="plant-a", station="s1"))
    policy.ingest(ev("pressure_drift", 0.5, plant_id="plant-a", station="s2"))
    assert policy.should_escalate_for("plant-a") is True
    assert policy.should_escalate_for("plant-b") is False
    # plant-b single fault should not escalate
    policy.ingest(ev("pressure_drift", 0.5, plant_id="plant-b", station="s3"))
    assert policy.should_escalate_for("plant-b") is False

def test_policy_clears_on_pop():
    policy = EventWindowPolicy(confidence_threshold=0.97, max_size=10, ttl_s=60)
    policy.ingest(ev("pressure_drift", 0.5, station="s1"))
    policy.ingest(ev("vib_high", 0.5, station="s2"))
    assert policy.should_escalate_for("plant-a")
    popped = policy.pop_window("plant-a")
    assert len(popped) == 2
    assert policy.should_escalate_for("plant-a") is False
    assert policy.window_sizes().get("plant-a", 0) == 0

def test_policy_ttl_expiry():
    policy = EventWindowPolicy(confidence_threshold=0.97, max_size=10, ttl_s=0.2)
    now = time.time()
    policy.ingest(ev("pressure_drift", 0.5, station="s1"), now=now)
    policy.ingest(ev("pressure_drift", 0.5, station="s2"), now=now)
    assert policy.should_escalate_for("plant-a", now=now) is True
    # after TTL
    assert policy.should_escalate_for("plant-a", now=now + 0.3) is False
    assert policy.events_for("plant-a", now=now + 0.3) == []

def test_policy_max_size_bound():
    policy = EventWindowPolicy(confidence_threshold=0.99, max_size=3, ttl_s=60)
    for i in range(5):
        policy.ingest(ev("none", 0.5, station=f"s{i}"))
    assert len(policy.events_for("plant-a")) == 3
    # should keep most recent 3
    stations = [e.station_id for e in policy.events_for("plant-a")]
    assert stations == ["s2", "s3", "s4"]

def test_pop_all_escalating():
    policy = EventWindowPolicy(confidence_threshold=0.97, max_size=10, ttl_s=60)
    policy.ingest(ev("pressure_drift", 0.5, plant_id="plant-a", station="s1"))
    policy.ingest(ev("pressure_drift", 0.5, plant_id="plant-a", station="s2"))
    policy.ingest(ev("pressure_drift", 0.5, plant_id="plant-b", station="s3"))
    # plant-b has only 1 → not escalating
    escalating = policy.pop_all_escalating()
    assert "plant-a" in escalating
    assert "plant-b" not in escalating
    assert len(escalating["plant-a"]) == 2
    # after pop, plant-a window empty
    assert policy.should_escalate_for("plant-a") is False
