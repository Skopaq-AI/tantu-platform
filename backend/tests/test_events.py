from backend.src.domain.events import DefectEvent, DefectClass, Track

def test_no_image_field():
    ev = DefectEvent(station_id="x", track=Track.LINE, defect_class=DefectClass.NONE, confidence=0.9, latency_ms=20)
    assert not hasattr(ev, "image_bytes")
    assert not hasattr(ev, "frame")

def test_orchestrator_policy():
    import asyncio
    from backend.src.application.orchestrator import Orchestrator
    from backend.src.adapters.reasoning_stub import DualStub
    orch = Orchestrator(DualStub())
    assert not orch.should_escalate()
    orch.ingest(DefectEvent(station_id="a", track=Track.LINE, defect_class=DefectClass.PRESSURE_DRIFT, confidence=0.96, latency_ms=20))
    assert not orch.should_escalate()
    orch.ingest(DefectEvent(station_id="b", track=Track.LINE, defect_class=DefectClass.VIB_HIGH, confidence=0.92, latency_ms=20))
    assert orch.should_escalate()
