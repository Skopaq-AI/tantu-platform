"""FFT fixtures — synthetic accelerometer windows → RMS + spectral peaks."""

import numpy as np
import pytest

from edge_perception.inference.vibration import analyze_vibration


def synth_vib(
    sample_rate_hz: float = 1000.0,
    duration_s: float = 1.0,
    freqs: list[tuple[float, float]] | None = None,
    noise_std: float = 0.08,
    seed: int = 7,
) -> np.ndarray:
    """Sum of sines + noise."""
    n = int(sample_rate_hz * duration_s)
    t = np.arange(n) / sample_rate_hz
    x = np.zeros(n)
    if freqs:
        for f, amp in freqs:
            x += amp * np.sin(2 * np.pi * f * t)
    rng = np.random.default_rng(seed)
    x += rng.normal(0, noise_std, n)
    return x


def test_rms_of_sine():
    # pure sine amp=1.0 → RMS = 1/√2 ≈0.707
    x = synth_vib(freqs=[(50, 1.0)], noise_std=0.0)
    res = analyze_vibration(x, 1000.0)
    assert abs(res.rms - 0.7071) < 0.04, f"rms {res.rms:.3f}"


def test_single_tone_peak():
    x = synth_vib(freqs=[(60, 1.5)], noise_std=0.02)
    res = analyze_vibration(x, 1000.0)
    # dominant should be ~60 Hz
    assert res.dominant_freq != 0
    assert abs(res.dominant_freq - 60) < 2.0, f"dominant {res.dominant_freq:.1f}"
    assert any(abs(f - 60) < 2.0 for f in res.peak_freqs), f"peaks {res.peak_freqs}"


def test_two_tones_both_found():
    x = synth_vib(freqs=[(30, 1.0), (120, 0.9)], noise_std=0.03)
    res = analyze_vibration(x, 1000.0, top_n=6)
    assert any(abs(f - 30) < 2.0 for f in res.peak_freqs), f"missing 30Hz in {res.peak_freqs}"
    assert any(abs(f - 120) < 2.5 for f in res.peak_freqs), f"missing 120Hz in {res.peak_freqs}"


def test_band_energies_with_shaft():
    # shaft 30 Hz, strong 1x + 2x
    x = synth_vib(freqs=[(30, 1.0), (60, 0.6)], noise_std=0.02)
    res = analyze_vibration(x, 1000.0, shaft_freq_hz=30)
    assert "1x" in res.band_energies and "2x" in res.band_energies
    assert res.band_energies["1x"] > 0.12
    assert res.band_energies["2x"] > 0.05


def test_crest_and_kurtosis_bump_on_impulse():
    # add periodic impulses (bearing fault proxy) — kurtosis should rise
    base = synth_vib(freqs=[(40, 0.8)], noise_std=0.05)
    # inject impulses every 0.1s
    imp = base.copy()
    for k in range(0, len(imp), 100):
        imp[k] += 4.0
    res_clean = analyze_vibration(base, 1000.0)
    res_imp = analyze_vibration(imp, 1000.0)
    assert res_imp.kurtosis > res_clean.kurtosis + 0.6, (
        f"kurt clean {res_clean.kurtosis:.2f} imp {res_imp.kurtosis:.2f}"
    )
    assert res_imp.crest_factor > res_clean.crest_factor


def test_empty_raises():
    with pytest.raises(ValueError):
        analyze_vibration(np.array([]), 1000.0)
    with pytest.raises(ValueError):
        analyze_vibration(np.array([1, 2, 3]), 0)


def test_latency_under_budget():
    x = synth_vib(freqs=[(50, 1.0), (100, 0.5)], noise_std=0.05)
    res = analyze_vibration(x, 2000.0)
    assert res.latency_ms < 80, f"fft latency {res.latency_ms:.1f}ms"
