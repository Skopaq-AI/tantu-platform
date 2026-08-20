"""Thermal probe — real calibration math."""

import pytest

from edge_perception.inference.thermal import ThermalConfig, ThermalProbe


def test_two_point_calibration_math():
    # probe reads 2°C high at low (raw 20 vs ref 18) and 3°C high at high (80 vs 77)
    cfg = ThermalConfig.from_two_point("p1", raw_low=20, ref_low=18, raw_high=80, ref_high=77)
    # check low/high map exactly
    assert abs(cfg.calibrate(20) - 18) < 1e-6
    assert abs(cfg.calibrate(80) - 77) < 1e-6
    # mid should interpolate
    mid = cfg.calibrate(50)
    assert 47 < mid < 49


def test_single_offset_scale_calibration():
    cfg = ThermalConfig(probe_id="p2", offset=-1.5, scale=0.98)
    assert abs(cfg.calibrate(100) - (98.5 * 0.98)) < 1e-6  # (100-1.5)*0.98
    # polynomial trim
    cfg2 = ThermalConfig(probe_id="p2", offset=0, scale=1.0, c2=1e-4)
    assert cfg2.calibrate(100) == pytest.approx(100 + 1e-4 * 10000)


def test_probe_read_with_injected_raw():
    cfg = ThermalConfig(probe_id="bearing-01", offset=0.0, scale=1.0)
    probe = ThermalProbe(cfg, read_fn=lambda: 65.3)
    res = probe.read()
    assert res.value == pytest.approx(65.3)
    assert res.quality == "good"
    assert res.probe_id == "bearing-01"
    assert res.raw == 65.3


def test_probe_range_guard():
    cfg = ThermalConfig(probe_id="p3", offset=0, scale=1.0, min_valid=0, max_valid=100)
    probe = ThermalProbe(cfg, read_fn=lambda: 140.0)
    res = probe.read()
    assert res.quality == "bad"
    assert any("out_of_range" in n for n in res.notes)


def test_probe_slew_guard():
    cfg = ThermalConfig(probe_id="p4", offset=0, scale=1.0, max_rate_c_per_s=5.0)
    vals = iter([20.0, 60.0])
    probe = ThermalProbe(cfg, read_fn=lambda: next(vals))
    r1 = probe.read()
    assert r1.quality == "good"
    # second read immediately jumps 40°C — should be slew flagged
    r2 = probe.read()
    assert r2.quality in ("uncertain", "bad")
    assert any("slew" in n for n in r2.notes)


def test_probe_two_point_via_probe():
    cfg = ThermalConfig(probe_id="p5", offset=0, scale=1.0)
    probe = ThermalProbe(cfg, read_fn=lambda: 50.0)
    new = probe.calibrate_two_point(raw_low=10, ref_low=12, raw_high=90, ref_high=88)
    # new calibration should be active
    assert probe.config.scale == pytest.approx(new.scale)
    # probe still reads with new cal
    res = probe.read()
    # raw 50 with that cal → check roughly
    expected = new.calibrate(50)
    assert abs(res.value - expected) < 1e-6


def test_probe_no_hardware_raises_without_fn(tmp_path):
    cfg = ThermalConfig(probe_id="no-such-28-000000000000")
    probe = ThermalProbe(cfg, read_fn=None)
    with pytest.raises(FileNotFoundError):
        probe.read()
