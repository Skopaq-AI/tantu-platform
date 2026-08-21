"""Camera gauge detection tests — synthetic image round-trip."""

import pytest

from adapter_fabric.adapters.camera.adapter import (
    GaugeCalibration,
    generate_synthetic_gauge_image,
    analyze_gauge_image,
    CameraAdapter,
)
from adapter_fabric.domain.models import AdapterConfig, Protocol, TagMapping


def test_gauge_calibration():
    cal = GaugeCalibration(min_angle=-135, max_angle=135, min_value=0, max_value=100)
    assert cal.angle_to_value(-135) == pytest.approx(0, abs=1e-6)
    assert cal.angle_to_value(0) == pytest.approx(50, abs=1e-6)
    assert cal.angle_to_value(135) == pytest.approx(100, abs=1e-6)
    assert cal.angle_to_value(200) == pytest.approx(100, abs=1e-6)  # clamped


def test_generate_and_analyze_gauge():
    cal = GaugeCalibration(min_angle=-135, max_angle=135, min_value=0, max_value=100)
    # generate synthetic gauge at 75
    try:
        has_cv2 = True
    except Exception:
        has_cv2 = False
    if not has_cv2:
        pytest.skip("opencv not installed")
    img = generate_synthetic_gauge_image(75, calibration=cal, size=400, noise=False)
    assert img is not None
    assert img.shape[0] == 400
    value, conf, angle, debug = analyze_gauge_image(img, cal)
    assert value is not None, f"detection failed: {debug}"
    # Allow +-8 tolerance due to Hough quantization and pixel aliasing
    assert value == pytest.approx(75, abs=8.0), (
        f"got {value} conf {conf} angle {angle} debug {debug}"
    )
    assert conf > 0.4


def test_generate_multiple_values():
    try:
        has_cv2 = True
    except Exception:
        has_cv2 = False
    if not has_cv2:
        pytest.skip("opencv not installed")
    cal = GaugeCalibration(min_angle=-135, max_angle=135, min_value=0, max_value=100)
    for v in [10, 50, 90]:
        img = generate_synthetic_gauge_image(v, calibration=cal, size=400, noise=False)
        value, conf, angle, debug = analyze_gauge_image(img, cal)
        assert value is not None and conf > 0.3, f"v={v} got {value} {debug}"
        assert value == pytest.approx(v, abs=10.0), f"v={v} got {value}"


@pytest.mark.asyncio
async def test_camera_adapter_inject():
    cal_d = dict(min_angle=-135, max_angle=135, min_value=0, max_value=100)
    cfg = AdapterConfig(
        adapter_id="cam-1",
        protocol=Protocol.CAMERA,
        station_id="line1-gauge01",
        tags=(TagMapping(source_tag="camera", metric="gauge_value", unit="bar"),),
        params={"calibration": cal_d},
        poll_interval_ms=0,
    )
    ad = CameraAdapter(cfg)
    try:
        has_cv2 = True
    except Exception:
        has_cv2 = False
    if not has_cv2:
        # synthetic fallback path
        readings = await ad._poll_once_impl()  # type: ignore
        assert len(readings) == 1
        assert readings[0].metric == "gauge_value"
        return
    cal = GaugeCalibration(min_angle=-135, max_angle=135, min_value=0, max_value=100)
    img = generate_synthetic_gauge_image(60, calibration=cal, size=400, noise=False)
    ad.inject_frame(img)
    readings = await ad._poll_once_impl()  # type: ignore
    assert len(readings) == 1
    assert readings[0].metric == "gauge_value"
    # injected gauge at 60 should read ~60 +- tolerance
    assert readings[0].value == pytest.approx(60, abs=10.0)


def test_no_image_field_in_defect_event():
    import dataclasses
    from adapter_fabric.domain.events import DefectEvent

    fields = {f.name for f in dataclasses.fields(DefectEvent)}
    for fname in fields:
        assert "image" not in fname.lower()
        assert "frame" not in fname.lower()
