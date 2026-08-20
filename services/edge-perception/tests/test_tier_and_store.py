"""Tier detection + store-and-forward offline-first."""

import asyncio
import pytest

from edge_perception.config import detect_tier, EdgeTier
from edge_perception.gateway.health import HealthAggregator
from edge_perception.gateway.store_forward import StoreForward, InMemoryStore
from edge_perception.ota.updater import OTAUpdater, OTAPackage
import hashlib, base64, hmac


def test_tier_env_mapping():
    assert detect_tier("pi5_hailo") == EdgeTier.PI5_HAILO
    assert detect_tier("PI5-HAILO") == EdgeTier.PI5_HAILO
    assert detect_tier("hailo") == EdgeTier.PI5_HAILO
    assert detect_tier("orin_nano") == EdgeTier.ORIN_NANO
    assert detect_tier("orin-nano") == EdgeTier.ORIN_NANO
    assert detect_tier("thor") == EdgeTier.THOR
    assert detect_tier("jetson_thor") == EdgeTier.THOR
    assert detect_tier("") == EdgeTier.PI5_HAILO
    assert detect_tier("unknown_xyz") == EdgeTier.PI5_HAILO


def test_inmemory_bounded():
    s = InMemoryStore(maxlen=3)
    for i in range(4):
        from edge_perception.gateway.store_forward import Queued
        s.push(Queued(stream="s", payload={"i": i}, ts=i))
    assert len(s) == 3
    assert s.dropped == 1


def test_health_aggregator():
    ha = HealthAggregator()
    assert ha.overall() == "unknown"
    ha.mark_ok("gauge", latency_ms=22)
    ha.mark_ok("vibration")
    assert ha.overall() == "ok"
    ha.mark_degraded("gauge", "slow")
    assert ha.overall() == "degraded"
    ha.mark_down("gauge", "no cam")
    assert ha.overall() == "degraded"
    ha.mark_down("vibration", "no imu")
    assert ha.overall() in ("down", "degraded")


@pytest.mark.asyncio
async def test_store_forward_offline_buffer_and_drain():
    # point at non-existent redis — must buffer, not raise
    sf = StoreForward(redis_url="redis://127.0.0.1:6399/0", stream="test:sf", max_buffer=10, drain_interval_s=0.15)
    await sf.start()
    try:
        r = await sf.enqueue({"station_id": "s1", "metric": "gauge_value", "value": "3.2"})
        assert r["stored"] == "buffer"
        assert sf.depth() == 1
        assert sf.status()["enqueued_total"] == 1
        # enqueue more
        for i in range(3):
            await sf.enqueue({"station_id": f"s{i}", "metric": "x", "value": str(i)})
        assert sf.depth() == 4
        # drain should be no-op while redis is down (returns 0)
        drained = await sf.drain_once()
        assert drained == 0
        assert sf.depth() == 4
    finally:
        await sf.stop()


@pytest.mark.asyncio
async def test_ota_happy_path_and_monotonic(tmp_path):
    secret = "test-hmac-secret"
    updater = OTAUpdater(current_version="0.1.0", hmac_secret=secret, state_path=tmp_path / "ota.json")
    data = b"fake-artifact-bytes-v0.2.0"
    sha = hashlib.sha256(data).hexdigest()
    sig = base64.b64encode(hmac.new(secret.encode(), sha.encode(), hashlib.sha256).digest()).decode()
    pkg = OTAPackage(version="0.2.0", sha256=sha, signature_b64=sig, artifact_bytes=data)
    out = await updater.stage(pkg, data=data)
    assert out["status"] == "ready_to_apply"
    applied = updater.apply()
    assert applied["version"] == "0.2.0"
    assert updater.current_version == "0.2.0"

    # older version must be rejected
    bad_data = b"older"
    bad_sha = hashlib.sha256(bad_data).hexdigest()
    bad_sig = base64.b64encode(hmac.new(secret.encode(), bad_sha.encode(), hashlib.sha256).digest()).decode()
    bad_pkg = OTAPackage(version="0.1.5", sha256=bad_sha, signature_b64=bad_sig, artifact_bytes=bad_data)
    with pytest.raises(ValueError, match="not newer"):
        await updater.stage(bad_pkg, data=bad_data)

    # sha mismatch must fail
    wrong_pkg = OTAPackage(version="0.3.0", sha256="0"*64, signature_b64=sig, artifact_bytes=data)
    with pytest.raises(ValueError, match="sha256"):
        await updater.stage(wrong_pkg, data=data)

    # rollback
    rb = updater.rollback()
    assert rb["version"] == "0.1.0"
    assert updater.current_version == "0.1.0"


@pytest.mark.asyncio
async def test_ota_bad_signature_rejected(tmp_path):
    secret = "s3cret"
    updater = OTAUpdater(current_version="1.0.0", hmac_secret=secret)
    data = b"hello"
    sha = hashlib.sha256(data).hexdigest()
    bad_sig = base64.b64encode(b"wrong-signature-32bytes-padding!!").decode()
    pkg = OTAPackage(version="1.1.0", sha256=sha, signature_b64=bad_sig, artifact_bytes=data)
    with pytest.raises(ValueError, match="signature"):
        await updater.stage(pkg, data=data)
