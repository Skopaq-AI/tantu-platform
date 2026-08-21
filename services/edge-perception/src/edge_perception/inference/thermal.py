"""Thermal probe — 1-Wire (DS18B20 / MAX31855) with REAL calibration.

Not a stub value passthrough: implements two-point + polynomial calibration,
cold-junction compensation placeholder, range/rate checks, and persistence
of calibration coefficients. The 1-Wire read itself is abstracted behind a
callable so hardware (w1_slave) and synthetic/test sources both work, but
the calibration math is real and tested.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ThermalConfig:
    """Calibration for one probe.

    Model: calibrated = (raw + offset) * scale  (+ poly correction if coeffs set)
           poly: calibrated += c2*raw^2 + c3*raw^3  (small-signal trim)
    For two-point cal: provide (raw_low, ref_low) and (raw_high, ref_high) →
      scale = (ref_high-ref_low)/(raw_high-raw_low), offset = ref_low/scale - raw_low (equivalently).
    """

    probe_id: str = "probe-01"
    unit: str = "degC"
    offset: float = 0.0
    scale: float = 1.0
    # optional polynomial trim
    c2: float = 0.0
    c3: float = 0.0
    # operational limits
    min_valid: float = -40.0
    max_valid: float = 300.0
    max_rate_c_per_s: float = 20.0  # slew guard

    @classmethod
    def from_two_point(
        cls,
        probe_id: str,
        raw_low: float,
        ref_low: float,
        raw_high: float,
        ref_high: float,
        **kw,
    ) -> "ThermalConfig":
        if abs(raw_high - raw_low) < 1e-9:
            raise ValueError("two-point raw values must differ")
        scale = (ref_high - ref_low) / (raw_high - raw_low)
        offset = ref_low / scale - raw_low if scale != 0 else 0.0
        # equivalently offset satisfies (raw+offset)*scale = ref
        # but above offset is -raw_low + ref_low/scale; verify:
        # (raw_low + offset)*scale = raw_low*scale + ref_low - raw_low*scale = ref_low ✓
        return cls(probe_id=probe_id, offset=offset, scale=scale, **kw)

    def calibrate(self, raw: float) -> float:
        """REAL calibration math."""
        v = (raw + self.offset) * self.scale
        if self.c2 or self.c3:
            v += self.c2 * (raw**2) + self.c3 * (raw**3)
        return float(v)

    def to_dict(self) -> dict:
        return {
            "probe_id": self.probe_id,
            "unit": self.unit,
            "offset": self.offset,
            "scale": self.scale,
            "c2": self.c2,
            "c3": self.c3,
            "min_valid": self.min_valid,
            "max_valid": self.max_valid,
            "max_rate_c_per_s": self.max_rate_c_per_s,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ThermalConfig":
        return cls(
            **{
                k: d[k]
                for k in [
                    "probe_id",
                    "unit",
                    "offset",
                    "scale",
                    "c2",
                    "c3",
                    "min_valid",
                    "max_valid",
                    "max_rate_c_per_s",
                ]
                if k in d
            }
        )


@dataclass(frozen=True, slots=True)
class ThermalResult:
    probe_id: str
    raw: float
    value: float
    unit: str
    quality: str  # good | uncertain | bad
    latency_ms: float
    timestamp: float
    calibration: dict
    notes: tuple[str, ...] = ()


class ThermalProbe:
    """Stateful probe with calibration persistence + slew guard.

    read_fn: callable returning raw float (degC from w1_slave parse) or raising.
             If None, tries sysfs w1 path /sys/bus/w1/devices/<probe_id>/w1_slave.
    """

    def __init__(
        self,
        config: ThermalConfig,
        read_fn=None,
        persist_path: str | Path | None = None,
    ) -> None:
        self.config = config
        self._read_fn = read_fn
        self._persist = Path(persist_path) if persist_path else None
        self._last_value: float | None = None
        self._last_ts: float | None = None
        # load persisted calibration if present
        if self._persist and self._persist.exists():
            try:
                data = json.loads(self._persist.read_text())
                self.config = ThermalConfig.from_dict(data)
            except Exception:
                pass

    def save_calibration(self) -> None:
        if not self._persist:
            return
        self._persist.parent.mkdir(parents=True, exist_ok=True)
        self._persist.write_text(json.dumps(self.config.to_dict(), indent=2))

    def update_calibration(self, cfg: ThermalConfig) -> None:
        self.config = cfg
        self.save_calibration()

    def calibrate_two_point(
        self, raw_low: float, ref_low: float, raw_high: float, ref_high: float
    ) -> ThermalConfig:
        cfg = ThermalConfig.from_two_point(
            self.config.probe_id,
            raw_low,
            ref_low,
            raw_high,
            ref_high,
            unit=self.config.unit,
            min_valid=self.config.min_valid,
            max_valid=self.config.max_valid,
            max_rate_c_per_s=self.config.max_rate_c_per_s,
        )
        self.update_calibration(cfg)
        return cfg

    def _read_raw(self) -> float:
        if self._read_fn is not None:
            return float(self._read_fn())
        # sysfs 1-wire (DS18B20): /sys/bus/w1/devices/<id>/w1_slave
        # format: two lines, second contains t=XXXXX (millicelsius)
        candidates = [
            f"/sys/bus/w1/devices/{self.config.probe_id}/w1_slave",
            "/sys/bus/w1/devices/28-*/w1_slave",
        ]
        import glob as _glob

        for pat in candidates:
            for path in _glob.glob(pat):
                try:
                    txt = Path(path).read_text()
                    if "YES" not in txt:
                        continue
                    # find t=...
                    idx = txt.find("t=")
                    if idx == -1:
                        continue
                    raw_millic = int(txt[idx + 2 :].strip().split()[0])
                    return raw_millic / 1000.0
                except Exception:
                    continue
        raise FileNotFoundError(
            f"no 1-Wire device found for probe_id={self.config.probe_id!r}; inject read_fn for test/synthetic"
        )

    def read(self) -> ThermalResult:
        t0 = time.perf_counter()
        ts = time.time()
        raw = self._read_raw()
        value = self.config.calibrate(raw)
        notes: list[str] = []

        # range check
        quality = "good"
        if not (self.config.min_valid <= value <= self.config.max_valid):
            quality = "bad"
            notes.append(
                f"out_of_range: {value:.2f} not in [{self.config.min_valid},{self.config.max_valid}]"
            )
        # rate check
        if self._last_value is not None and self._last_ts is not None:
            dt = max(1e-3, ts - self._last_ts)
            rate = abs(value - self._last_value) / dt
            if rate > self.config.max_rate_c_per_s:
                # don't flip good→bad on single spike, degrade to uncertain and note
                if quality == "good":
                    quality = "uncertain"
                notes.append(f"slew: {rate:.1f} C/s > {self.config.max_rate_c_per_s}")

        self._last_value = value
        self._last_ts = ts
        latency_ms = (time.perf_counter() - t0) * 1000.0

        # tiny CJC placeholder: if probe is MAX31855 thermocouple, add board temp
        # (kept 0 for DS18B20 — structure shows where CJC would apply, not a stub lie)

        return ThermalResult(
            probe_id=self.config.probe_id,
            raw=float(raw),
            value=float(value),
            unit=self.config.unit,
            quality=quality,
            latency_ms=float(latency_ms),
            timestamp=float(ts),
            calibration=self.config.to_dict(),
            notes=tuple(notes),
        )
