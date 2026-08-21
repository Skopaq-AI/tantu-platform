"""CT-clamp current signature — REAL: RMS + harmonic signature from current waveform.

SCT-013 / similar clamp → burden resistor → ADC. From a window of raw ADC-derived
current samples (A), this module extracts: RMS, peak, crest, THD, harmonic content
(FFT), and a simple load signature (resistive / inductive / nonlinear).
No ML stub — deterministic spectral signature.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
from scipy.signal import get_window


@dataclass(frozen=True, slots=True)
class CTClampResult:
    rms_a: float
    peak_a: float
    crest_factor: float
    thd_percent: float
    fundamental_hz: float
    fundamental_mag: float
    harmonics: dict[int, float]  # harmonic number → relative mag (fraction of fund)
    signature: str  # resistive | inductive | nonlinear | off | unknown
    power_proxy_w: float  # Vrms assumed or 230V nominal for proxy
    latency_ms: float
    n_samples: int
    sample_rate_hz: float
    quality: str


def analyze_ct(
    samples: np.ndarray,
    sample_rate_hz: float,
    *,
    mains_hz: float = 50.0,
    nominal_vrms: float = 230.0,
    window: str = "hann",
) -> CTClampResult:
    """Analyze a CT current window.

    samples: current in Amps (already scaled from ADC via burden/cal).
    sample_rate_hz: e.g. 2000–8000 Hz is typical for mains harmonics to ~15th.
    """
    t0 = time.perf_counter()
    if samples is None or samples.size == 0:
        raise ValueError("empty CT window")
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be >0")
    x = np.asarray(samples, dtype=np.float64).ravel()
    if x.size < 32:
        raise ValueError("CT window too short (≥32)")
    # remove DC bias (clamp/ADC offset)
    x = x - float(np.mean(x))
    n = x.size

    win = get_window(window, n, fftbins=True)
    cg = float(np.mean(win))
    xw = x * win

    rms = float(np.sqrt(np.mean(x * x)))
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    crest = float(peak / rms) if rms > 1e-9 else 0.0

    if rms < 0.04:
        # essentially off / open clamp
        return CTClampResult(
            rms_a=rms,
            peak_a=peak,
            crest_factor=crest,
            thd_percent=0.0,
            fundamental_hz=mains_hz,
            fundamental_mag=0.0,
            harmonics={},
            signature="off" if rms < 0.015 else "unknown",
            power_proxy_w=rms * nominal_vrms,
            latency_ms=(time.perf_counter() - t0) * 1000,
            n_samples=n,
            sample_rate_hz=float(sample_rate_hz),
            quality="good" if rms < 0.015 else "uncertain",
        )

    spec = np.fft.rfft(xw)
    freqs = np.fft.rfftfreq(n, d=1.0 / sample_rate_hz)
    mag = np.abs(spec) / (n * cg * 0.5)
    mag[0] = 0.0

    # fundamental: strongest peak near mains_hz within ±3 Hz
    fund_mask = (freqs >= mains_hz - 3) & (freqs <= mains_hz + 3)
    if np.any(fund_mask):
        idx_fund = int(np.argmax(mag * fund_mask))
        # but argmax over masked needs the global idx
        fund_candidates = np.where(fund_mask)[0]
        idx_fund = fund_candidates[int(np.argmax(mag[fund_candidates]))]
    else:
        # fallback: global max
        idx_fund = int(np.argmax(mag))
    fund_hz = float(freqs[idx_fund])
    fund_mag = float(mag[idx_fund])
    if fund_mag < 1e-12:
        fund_mag = 1e-12

    # harmonic relative magnitudes (2..15)
    harmonics: dict[int, float] = {}
    harm_power = 0.0
    for h in range(2, 16):
        fc = mains_hz * h
        if fc >= sample_rate_hz / 2 - 1:
            break
        # ±2 Hz window around harmonic
        m = (freqs >= fc - 2) & (freqs <= fc + 2)
        if not np.any(m):
            continue
        hm = float(np.max(mag[m]))
        rel = hm / fund_mag
        if rel > 0.015:  # 1.5 % threshold
            harmonics[h] = float(rel)
            harm_power += hm * hm
    thd = float(np.sqrt(harm_power) / fund_mag * 100.0)

    # signature — heuristic, deterministic
    # resistive: low THD (<8%), crest ~1.41, harmonics weak
    # inductive (motor): moderate even harmonics, 5th/7th present, crest ~1.6-2.0
    # nonlinear (VFD/SMPS): high THD (>15%), strong odd harmonics 3,5,7
    if rms < 0.05:
        sig = "off"
    elif thd < 8.0 and max(harmonics.values(), default=0) < 0.08:
        sig = "resistive"
    elif thd > 18.0 or (harmonics.get(3, 0) > 0.18 and harmonics.get(5, 0) > 0.10):
        sig = "nonlinear"
    elif harmonics.get(2, 0) > 0.06 or harmonics.get(5, 0) > 0.08:
        sig = "inductive"
    else:
        sig = "unknown"

    quality = "good"
    if thd > 25 or crest > 3.2:
        quality = "uncertain"

    power_proxy = float(rms * nominal_vrms)  # real power would need voltage phase; proxy only

    return CTClampResult(
        rms_a=rms,
        peak_a=peak,
        crest_factor=crest,
        thd_percent=thd,
        fundamental_hz=fund_hz,
        fundamental_mag=fund_mag,
        harmonics=harmonics,
        signature=sig,
        power_proxy_w=power_proxy,
        latency_ms=(time.perf_counter() - t0) * 1000,
        n_samples=n,
        sample_rate_hz=float(sample_rate_hz),
        quality=quality,
    )
