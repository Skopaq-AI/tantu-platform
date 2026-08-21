"""CT clamp — synthetic mains waveforms."""

import numpy as np
import pytest

from edge_perception.inference.ct_clamp import analyze_ct


def synth_current(
    sample_rate=2000, duration=0.6, fundamental_a=2.0, harmonics=None, mains_hz=50.0, seed=1
):
    n = int(sample_rate * duration)
    t = np.arange(n) / sample_rate
    x = fundamental_a * np.sqrt(2) * np.sin(2 * np.pi * mains_hz * t)
    # fundamental_a is RMS; peak = RMS*sqrt2 — so time series is correct
    if harmonics:
        for h, rel in harmonics.items():
            amp_rms = fundamental_a * rel
            x += amp_rms * np.sqrt(2) * np.sin(2 * np.pi * mains_hz * h * t)
    # small noise
    rng = np.random.default_rng(seed)
    x += rng.normal(0, 0.02, n)
    return x


def test_rms_resistive_clean():
    x = synth_current(fundamental_a=3.0, harmonics=None)
    res = analyze_ct(x, 2000, mains_hz=50.0)
    assert abs(res.rms_a - 3.0) < 0.18, f"rms {res.rms_a:.3f}"
    assert res.signature == "resistive"
    assert res.thd_percent < 8.0


def test_nonlinear_high_thd():
    # strong 3rd/5th
    x = synth_current(fundamental_a=2.0, harmonics={3: 0.28, 5: 0.18, 7: 0.10})
    res = analyze_ct(x, 2000)
    assert res.thd_percent > 18, f"thd {res.thd_percent:.1f}"
    assert res.signature == "nonlinear"
    assert 3 in res.harmonics and 5 in res.harmonics


def test_off_detection():
    x = np.random.normal(0, 0.005, 1200)
    res = analyze_ct(x, 2000)
    assert res.signature == "off"
    assert res.rms_a < 0.04


def test_empty_raises():
    with pytest.raises(ValueError):
        analyze_ct(np.array([]), 2000)
    with pytest.raises(ValueError):
        analyze_ct(np.array([1, 2, 3]), 0)
