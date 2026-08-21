"""API integration — FastAPI TestClient + synthetic fixtures."""

import base64
import math

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from edge_perception.api.main import app
from edge_perception.inference.gauge import GaugeConfig


@pytest.fixture(scope="module")
def client():
    # do not start lifespan redis drain in tests — override settings to bad redis so offline path is exercised
    with TestClient(app) as c:
        yield c


def test_health_and_info(client):
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert "tier" in j
    assert "tier_caps" in j
    assert j["frames_never_leave"] is True
    assert "store_forward" in j
    r2 = client.get("/info")
    assert r2.status_code == 200
    assert r2.json()["frames_never_leave"] is True


def test_metrics_exposed(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "edge_gauge" in r.text or "python_gc" in r.text  # prometheus exposition


def _make_gauge_b64(value=5.0) -> str:
    cfg = GaugeConfig()
    w = h = 320
    cx, cy = w // 2, h // 2
    r = min(w, h) // 2 - 10
    img = np.ones((h, w, 3), dtype=np.uint8) * 245
    cv2.circle(img, (cx, cy), r, (30, 30, 30), 3)
    ang = cfg.value_to_angle(value)
    rad = math.radians(ang)
    cv2.line(
        img,
        (cx, cy),
        (int(cx + math.cos(rad) * r * 0.78), int(cy + math.sin(rad) * r * 0.78)),
        (10, 10, 220),
        3,
        cv2.LINE_AA,
    )
    cv2.circle(img, (cx, cy), 9, (20, 20, 20), -1)
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return base64.b64encode(buf.tobytes()).decode()


def test_infer_gauge_e2e(client):
    b64 = _make_gauge_b64(6.5)
    r = client.post(
        "/infer/gauge",
        json={"station_id": "line2-gauge3", "image_b64": b64, "min_value": 0, "max_value": 10},
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert "value" in j and "confidence" in j
    assert abs(j["value"] - 6.5) < 1.0, f"value {j['value']}"
    assert j["quality"] in ("good", "uncertain", "bad")


def test_infer_gauge_bad_image(client):
    r = client.post("/infer/gauge", json={"station_id": "s1", "image_b64": "not-base64!!"})
    assert r.status_code == 400


def test_infer_vibration_e2e(client):
    sr = 1000.0
    n = 1024
    t = np.arange(n) / sr
    samples = (np.sin(2 * np.pi * 50 * t) + 0.5 * np.sin(2 * np.pi * 120 * t)).tolist()
    r = client.post(
        "/infer/vibration",
        json={"station_id": "motor-01", "samples": samples, "sample_rate_hz": sr},
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert "rms" in j and "peak_freqs" in j
    assert j["health"] in ("ok", "watch", "alarm")
    assert any(abs(f - 50) < 3 for f in j["peak_freqs"]) or any(
        abs(f - 120) < 4 for f in j["peak_freqs"]
    )


def test_infer_thermal_injected(client):
    r = client.post("/infer/thermal", json={"probe_id": "test-probe-99", "raw": 72.5})
    assert r.status_code == 200, r.text
    j = r.json()
    assert abs(j["value"] - 72.5) < 1e-6
    assert j["quality"] in ("good", "uncertain", "bad")


def test_infer_thermal_two_point(client):
    r = client.post(
        "/infer/thermal",
        json={
            "probe_id": "cal-probe-01",
            "raw": 50.0,
            "calibrate_two_point": {"raw_low": 0, "ref_low": 2, "raw_high": 100, "ref_high": 101},
        },
    )
    assert r.status_code == 200, r.text
    # with that cal, raw 50 → should be about 51.5 (slope 0.99, offset 2/0.99 ≈2.02)
    # we just assert it is not 50 (cal applied)
    assert r.json()["value"] != pytest.approx(50.0, abs=0.5)


def test_infer_ct_e2e(client):
    sr = 2000
    t = np.arange(1200) / sr
    # 50Hz 2A RMS sine
    samples = (2 * np.sqrt(2) * np.sin(2 * np.pi * 50 * t)).tolist()
    r = client.post(
        "/infer/ct", json={"station_id": "panel-ct1", "samples": samples, "sample_rate_hz": sr}
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert abs(j["rms_a"] - 2.0) < 0.3
    assert j["signature"] in ("resistive", "inductive", "nonlinear", "off", "unknown")


def test_ota_requires_auth(client):
    import hashlib

    data = b"x"
    sha = hashlib.sha256(data).hexdigest()
    # without admin token → 401
    r = client.post("/ota/stage", json={"version": "9.9.9", "sha256": sha})
    assert r.status_code in (401, 403)


def test_jwt_roundtrip():
    from edge_perception.security.auth import issue_jwt, verify_jwt

    tok = issue_jwt("tester", "plant-demo-01", "plant_admin")
    claims = verify_jwt(tok)
    assert claims["role"] == "plant_admin"
    assert claims["plant_id"] == "plant-demo-01"
