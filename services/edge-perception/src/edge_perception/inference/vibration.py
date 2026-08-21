"""Vibration FFT — REAL numpy/scipy: window → RMS + spectral peaks + health."""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
from scipy.signal import find_peaks, get_window


@dataclass(frozen=True, slots=True)
class VibrationResult:
    rms: float
    peak_freqs: tuple[float, ...]
    peak_mags: tuple[float, ...]
    peak_proms: tuple[float, ...]
    dominant_freq: float
    crest_factor: float
    kurtosis: float
    latency_ms: float
    # health hint derived from spectrum (not a stub — real band-energy check)
    band_energies: dict[str, float]  # e.g. {"1x":..., "2x":..., "high":...}
    health: str  # ok | watch | alarm
    n_samples: int
    sample_rate_hz: float


def _kurtosis(x: np.ndarray) -> float:
    m = float(np.mean(x))
    var = float(np.mean((x - m) ** 2))
    if var < 1e-12:
        return 3.0
    m4 = float(np.mean((x - m) ** 4))
    return m4 / (var * var)


def analyze_vibration(
    samples: np.ndarray,
    sample_rate_hz: float,
    *,
    shaft_freq_hz: float | None = None,
    window: str = "hann",
    top_n: int = 5,
    min_peak_prom_db: float = 6.0,
) -> VibrationResult:
    """REAL FFT analysis.

    Args:
        samples: 1-D accelerometer window (g or mm/s² — unit-agnostic, RMS in same unit).
        sample_rate_hz: sampling rate.
        shaft_freq_hz: expected shaft 1× frequency for band-energy (if None, no band split).
        window: scipy window name.
        top_n: max peaks returned.
        min_peak_prom_db: minimum prominence in dB relative to median spectral floor.
    """
    t0 = time.perf_counter()
    if samples is None or samples.size == 0:
        raise ValueError("empty vibration window")
    x = np.asarray(samples, dtype=np.float64).ravel()
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be >0")
    if x.size < 16:
        raise ValueError("window too short (need ≥16 samples)")

    # detrend (remove DC / gravity bias)
    x = x - float(np.mean(x))
    n = x.size

    # window + FFT
    win = get_window(window, n, fftbins=True)
    xw = x * win
    # coherent gain correction for Hann etc.
    cg = float(np.mean(win))
    # RMS is time-domain, window-corrected implicitly by cg? Use unwindowed for RMS.
    rms = float(np.sqrt(np.mean(x * x)))
    peak_val = float(np.max(np.abs(x))) if x.size else 0.0
    crest = float(peak_val / rms) if rms > 1e-12 else 0.0
    kurt = float(_kurtosis(x))

    # one-sided spectrum
    spec = np.fft.rfft(xw)
    freqs = np.fft.rfftfreq(n, d=1.0 / sample_rate_hz)
    # magnitude, window-corrected, scaled to amplitude (not power)
    mag = np.abs(spec) / (
        n * cg * 0.5
    )  # 0.5 because one-sided doubles energy; close enough for peaks
    mag[0] = 0.0  # ignore DC after detrend

    # spectral floor for prominence threshold
    # prominence in linear; convert db to linear factor
    floor = float(np.median(mag[1:])) if mag.size > 2 else 0.0
    prom_lin = (
        floor * (10.0 ** (min_peak_prom_db / 20.0)) if floor > 1e-12 else float(np.max(mag) * 0.08)
    )

    # find peaks
    peaks_idx, props = find_peaks(mag, prominence=prom_lin, distance=max(2, int(len(freqs) / 400)))
    prominences = props.get("prominences", np.array([]))

    # rank by magnitude (or prominence-weighted)
    if peaks_idx.size > 0:
        order = np.argsort(mag[peaks_idx])[::-1]
        peaks_idx = peaks_idx[order]
        prominences = (
            prominences[order] if prominences.size else np.zeros_like(peaks_idx, dtype=float)
        )
        if top_n is not None:
            peaks_idx = peaks_idx[:top_n]
            prominences = prominences[:top_n]
        peak_freqs = tuple(float(freqs[i]) for i in peaks_idx)
        peak_mags = tuple(float(mag[i]) for i in peaks_idx)
        peak_proms = tuple(float(p) for p in prominences)
        dominant = float(peak_freqs[0])
    else:
        peak_freqs, peak_mags, peak_proms = (), (), ()
        dominant = 0.0

    # band energies — if shaft freq given, split into 1×, 2×, 3×, high (>3.5×) + sub
    band_energies: dict[str, float] = {}
    if shaft_freq_hz and shaft_freq_hz > 0:
        # power proxy = mag^2
        power = mag * mag
        total = float(np.sum(power)) + 1e-12

        def band(fc: float, bw_frac: float = 0.12) -> float:
            lo = fc * (1 - bw_frac)
            hi = fc * (1 + bw_frac)
            m = (freqs >= lo) & (freqs <= hi)
            return float(np.sum(power[m]) / total)

        band_energies = {
            "sub": float(np.sum(power[freqs < shaft_freq_hz * 0.85]) / total),
            "1x": band(shaft_freq_hz),
            "2x": band(2 * shaft_freq_hz),
            "3x": band(3 * shaft_freq_hz),
            "high": float(np.sum(power[freqs > 3.5 * shaft_freq_hz]) / total),
        }
    else:
        # generic low/mid/high split by Nyquist thirds
        power = mag * mag
        total = float(np.sum(power)) + 1e-12
        nyq = sample_rate_hz / 2
        band_energies = {
            "low": float(np.sum(power[freqs < nyq / 3]) / total),
            "mid": float(np.sum(power[(freqs >= nyq / 3) & (freqs < 2 * nyq / 3)]) / total),
            "high": float(np.sum(power[freqs >= 2 * nyq / 3]) / total),
        }

    # health — simple rule stack (tunable via config in prod)
    # thresholds inspired by ISO 10816-ish structure but relative (no absolute unit assumed)
    health = "ok"
    if rms > 4.5 or crest > 6.0 or kurt > 6.0:
        health = "alarm"
    elif rms > 2.8 or crest > 4.0 or kurt > 4.2:
        health = "watch"
    # spectral alarm: strong 2× or high band suggests bearing/misalignment
    if band_energies.get("2x", 0) > 0.18 or band_energies.get("high", 0) > 0.35:
        health = "alarm" if health == "watch" else ("watch" if health == "ok" else health)

    latency_ms = (time.perf_counter() - t0) * 1000.0
    return VibrationResult(
        rms=rms,
        peak_freqs=peak_freqs,
        peak_mags=peak_mags,
        peak_proms=peak_proms,
        dominant_freq=dominant,
        crest_factor=crest,
        kurtosis=kurt,
        latency_ms=latency_ms,
        band_energies=band_energies,
        health=health,
        n_samples=int(n),
        sample_rate_hz=float(sample_rate_hz),
    )
