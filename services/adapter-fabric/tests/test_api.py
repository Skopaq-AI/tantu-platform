"""API integration tests."""
import pytest
from fastapi.testclient import TestClient

from adapter_fabric.infra.security import issue_jwt


def _auth_header(plant_id="plant-demo-01", role="plant_admin"):
    tok = issue_jwt(sub="tester", plant_id=plant_id, role=role)
    return {"Authorization": f"Bearer {tok}"}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j["service"] == "adapter-fabric"
    assert "adapters" in j


def test_info(client):
    r = client.get("/info")
    assert r.status_code == 200
    assert "frames_never_leave" in r.json()


def test_metrics(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]


def test_auth_required_for_register(client):
    r = client.post("/adapters", json={"adapter_id": "x-1", "protocol": "opcua", "station_id": "s1"})
    assert r.status_code == 401


def test_register_and_poll_modbus(client, auth_header):
    body = {
        "adapter_id": "modbus-test-1",
        "protocol": "modbus",
        "station_id": "line1-plc01",
        "enabled": False,
        "tags": [{"source_tag": "3:100", "metric": "pressure_bar", "unit": "bar", "scale": 0.1, "offset": 0, "data_type": "uint16"}],
        "params": {"host": "127.0.0.1", "port": 5020},
        "poll_interval_ms": 0,
    }
    r = client.post("/adapters", json=body, headers=auth_header)
    assert r.status_code == 200, r.text
    r = client.get("/adapters", headers=auth_header)
    assert r.status_code == 200
    ids = [a["adapter_id"] for a in r.json()]
    assert "modbus-test-1" in ids

    # poll (synthetic fallback because no real PLC)
    r = client.post("/adapters/modbus-test-1/poll", headers=auth_header)
    assert r.status_code == 200
    readings = r.json()
    assert len(readings) == 1
    assert readings[0]["metric"] == "pressure_bar"
    assert "value" in readings[0]
    assert "unit" in readings[0]

    # delete
    r = client.delete("/adapters/modbus-test-1", headers=auth_header)
    assert r.status_code == 200


def test_register_camera_and_opcua(client, auth_header):
    for proto, tag in [("camera", "camera"), ("opcua", "ns=2;i=1001")]:
        aid = f"{proto}-api-1"
        body = {
            "adapter_id": aid,
            "protocol": proto,
            "station_id": "s1",
            "enabled": False,
            "tags": [{"source_tag": tag, "metric": "gauge_value" if proto == "camera" else "pressure_bar", "unit": "bar"}],
            "params": {"calibration": {"min_angle": -135, "max_angle": 135, "min_value": 0, "max_value": 100}} if proto == "camera" else {"endpoint": "opc.tcp://localhost:4840"},
            "poll_interval_ms": 0,
        }
        r = client.post("/adapters", json=body, headers=auth_header)
        assert r.status_code == 200, r.text
        r = client.post(f"/adapters/{aid}/poll", headers=auth_header)
        assert r.status_code == 200
        assert len(r.json()) == 1
        client.delete(f"/adapters/{aid}", headers=auth_header)


def test_tag_map_preview(client):
    r = client.post("/tag-map/preview", json={"formula": "(a + b) / 2", "variables": {"a": 10, "b": 20}})
    assert r.status_code == 200
    assert r.json()["value"] == pytest.approx(15.0)
    r = client.post("/tag-map/preview", json={"formula": "__import__('os').system('x')", "variables": {}})
    assert r.status_code == 422


def test_ingest(client):
    r = client.post("/ingest", json={"station_id": "line1-s01", "metric": "pressure_bar", "value": 9.5, "unit": "bar", "protocol": "mqtt"})
    assert r.status_code == 200
    j = r.json()
    assert "reading" in j
    assert j["defect"] is not None  # 9.5 bar -> pressure drift
    assert j["defect"]["defect_class"] == "pressure_drift"


def test_openapi(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    j = r.json()
    assert "paths" in j
    assert "/health" in j["paths"]
    assert "/adapters" in j["paths"]
    assert "/metrics" in j["paths"]


def test_defect_event_has_no_image():
    from adapter_fabric.domain.events import DefectEvent
    import dataclasses
    fields = {f.name for f in dataclasses.fields(DefectEvent)}
    assert "image" not in fields
    assert "frame" not in fields
