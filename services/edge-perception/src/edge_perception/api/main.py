"""FastAPI service — edge-perception on :8002.

Route contract:
  GET  /health              — tier + component health + store-forward + OTA, no auth
  GET  /metrics             — Prometheus exposition, no auth
  GET  /info                — tier caps
  POST /infer/gauge         — image_b64 → value (auth optional, enforced if JWT_SECRET != dev)
  POST /infer/vibration     — FFT
  POST /infer/thermal       — 1-Wire + calibration
  POST /infer/ct            — CT clamp
  POST /ota/stage           — stage OTA package (RBAC: plant_admin)
  POST /ota/apply           — apply staged (RBAC)
  POST /ota/rollback        — rollback (RBAC)
  GET  /ota/status          — OTA status

Offline-first: infer results are also enqueued to Redis stream store-and-forward;
on transient Redis failure they buffer in memory and drain when Redis returns.
"""

from __future__ import annotations

import base64
import os
import time
from contextlib import asynccontextmanager

import cv2
import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ..config import get_settings
from ..gateway.health import HealthAggregator
from ..gateway.store_forward import StoreForward
from ..inference.ct_clamp import analyze_ct
from ..inference.gauge import GaugeConfig, gauge_quality, read_gauge
from ..inference.thermal import ThermalConfig, ThermalProbe
from ..inference.vibration import analyze_vibration
from ..ota.updater import OTAUpdater, OTAPackage
from ..security.auth import RBAC, require_auth
from .schemas import (
    CTInferIn,
    CTOut,
    GaugeInferIn,
    GaugeInferOut,
    OTAStageIn,
    ThermalOut,
    ThermalReadIn,
    VibrationInferIn,
    VibrationInferOut,
)
import edge_perception.metrics as m

settings = get_settings()
health = HealthAggregator()
sf = StoreForward(
    redis_url=settings.redis_url,
    stream=settings.redis_stream,
    max_buffer=settings.redis_max_buffer,
)
ota = OTAUpdater(
    current_version=settings.ota_current_version,
    public_key_path=settings.ota_public_key_path or None,
    hmac_secret=os.getenv("JWT_SECRET", os.getenv("JWT_PRIVATE_KEY", "")),
    state_path="/tmp/tantu-edge-ota.json",
)

# single probe registry (in prod, one per w1 id)
_probes: dict[str, ThermalProbe] = {}


def _get_probe(probe_id: str) -> ThermalProbe:
    if probe_id not in _probes:
        cfg = ThermalConfig(probe_id=probe_id)
        _probes[probe_id] = ThermalProbe(cfg)
    return _probes[probe_id]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup — store-forward + health seeds
    try:
        await sf.start()
        health.mark_ok("store_forward", details=sf.status())
    except Exception as e:
        health.mark_degraded("store_forward", str(e))
    health.mark_ok("api", details={"tier": settings.tier.value})
    # mark inference components ok (they are pure functions)
    for name in ("gauge", "vibration", "thermal", "ct"):
        health.mark_ok(name)
    # OTA
    try:
        m.ota_version_info.labels(version=ota.current_version).set(1)
    except Exception:
        pass
    yield
    try:
        await sf.stop()
    except Exception:
        pass


app = FastAPI(
    title="TANTU Edge Perception",
    version="0.1.0",
    description="Tiered offline-first edge inference — gauge CV + vibration FFT + thermal + CT. Frames never leave.",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
async def health_ep():
    snap = health.snapshot()
    # refresh store-forward status
    snap["components"]["store_forward"] = {
        "status": "ok" if sf.status()["redis_ok"] else "degraded",
        "details": sf.status(),
    }
    return {
        **snap,
        "tier": settings.tier.value,
        "tier_caps": settings.tier_caps,
        "store_forward": sf.status(),
        "ota": ota.status(),
    }


@app.get("/info")
async def info():
    return {
        "name": "edge-perception",
        "version": "0.1.0",
        "tier": settings.tier.value,
        "tier_caps": settings.tier_caps,
        "frames_never_leave": True,
        "port": 8002,
    }


@app.get("/metrics")
async def metrics():
    # sync store_forward gauge
    try:
        m.store_forward_buffered.set(float(sf.depth()))
    except Exception:
        pass
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ——— gauge ———


@app.post("/infer/gauge", response_model=GaugeInferOut)
async def infer_gauge(body: GaugeInferIn, claims: dict | None = Depends(require_auth)):
    _t0 = time.perf_counter()
    try:
        raw = base64.b64decode(body.image_b64)
        arr = np.frombuffer(raw, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("could not decode image (send JPEG/PNG base64)")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid image_b64: {e}")

    cfg = GaugeConfig(
        min_value=body.min_value,
        max_value=body.max_value,
        min_angle_deg=body.min_angle_deg,
        max_angle_deg=body.max_angle_deg,
    )
    try:
        res = read_gauge(img, cfg)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    qual = gauge_quality(res.confidence)
    ts = time.time()
    latency_ms = res.latency_ms

    # metrics
    try:
        m.gauge_readings_total.labels(tier=settings.tier.value, quality=qual).inc()
        m.gauge_confidence.observe(res.confidence)
        m.gauge_latency_ms.observe(latency_ms)
        m.gauge_value.labels(station_id=body.station_id).set(res.value)
    except Exception:
        pass

    # health latency
    budget = float(settings.tier_caps.get("gauge_budget_ms", 40))
    if latency_ms > budget * 1.6:
        health.mark_degraded("gauge", f"latency {latency_ms:.1f}ms > budget {budget}ms")
    else:
        health.mark_ok("gauge", latency_ms=latency_ms)

    # store-and-forward (offline-first, never blocks inference)
    try:
        await sf.enqueue(
            {
                "station_id": body.station_id,
                "metric": "gauge_value",
                "value": str(res.value),
                "unit": "bar",
                "confidence": str(res.confidence),
                "quality": qual,
                "latency_ms": str(latency_ms),
                "tier": settings.tier.value,
                "ts": str(ts),
                "protocol": "camera",
                "angle_deg": str(res.angle_deg),
            }
        )
        m.store_forward_enqueued_total.labels(dest="gauge").inc()
        m.store_forward_buffered.set(float(sf.depth()))
    except Exception:
        try:
            m.store_forward_failed_total.inc()
        except Exception:
            pass

    return GaugeInferOut(
        station_id=body.station_id,
        value=res.value,
        angle_deg=res.angle_deg,
        confidence=res.confidence,
        quality=qual,  # type: ignore
        latency_ms=latency_ms,
        centre=res.centre,
        radius=res.radius,
        tier=settings.tier.value,
        timestamp=ts,
        debug=res.debug,
    )


# ——— vibration ———


@app.post("/infer/vibration", response_model=VibrationInferOut)
async def infer_vibration(body: VibrationInferIn, claims: dict | None = Depends(require_auth)):
    if not body.samples:
        raise HTTPException(status_code=400, detail="samples empty")
    arr = np.asarray(body.samples, dtype=np.float64)
    try:
        res = analyze_vibration(arr, body.sample_rate_hz, shaft_freq_hz=body.shaft_freq_hz)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    ts = time.time()
    try:
        m.vibration_windows_total.labels(tier=settings.tier.value, health=res.health).inc()
        m.vibration_rms.labels(station_id=body.station_id).set(res.rms)
        m.vibration_latency_ms.observe(res.latency_ms)
    except Exception:
        pass

    budget = float(settings.tier_caps.get("fft_budget_ms", 20))
    if res.latency_ms > budget * 1.8:
        health.mark_degraded("vibration", f"fft {res.latency_ms:.1f}ms > {budget}ms")
    else:
        health.mark_ok("vibration", latency_ms=res.latency_ms)

    try:
        await sf.enqueue(
            {
                "station_id": body.station_id,
                "metric": "vibration_rms",
                "value": str(res.rms),
                "unit": body.unit,
                "health": res.health,
                "dominant_freq": str(res.dominant_freq),
                "crest": str(res.crest_factor),
                "tier": settings.tier.value,
                "ts": str(ts),
            }
        )
        m.store_forward_enqueued_total.labels(dest="vibration").inc()
    except Exception:
        pass

    return VibrationInferOut(
        station_id=body.station_id,
        rms=res.rms,
        unit=body.unit,
        peak_freqs=list(res.peak_freqs),
        peak_mags=list(res.peak_mags),
        dominant_freq=res.dominant_freq,
        crest_factor=res.crest_factor,
        kurtosis=res.kurtosis,
        band_energies=res.band_energies,
        health=res.health,  # type: ignore
        latency_ms=res.latency_ms,
        n_samples=res.n_samples,
        sample_rate_hz=res.sample_rate_hz,
        tier=settings.tier.value,
        timestamp=ts,
    )


# ——— thermal ———


@app.post("/infer/thermal", response_model=ThermalOut)
async def infer_thermal(body: ThermalReadIn, claims: dict | None = Depends(require_auth)):
    probe = _get_probe(body.probe_id)

    # optional two-point recalibration
    if body.calibrate_two_point:
        c = body.calibrate_two_point
        try:
            _cfg = probe.calibrate_two_point(
                float(c["raw_low"]), float(c["ref_low"]), float(c["raw_high"]), float(c["ref_high"])
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"calibration error: {e}")

    # if raw injected (test/synthetic), monkey the read_fn for this call
    if body.raw is not None:
        orig = probe._read_fn
        probe._read_fn = lambda: float(body.raw)  # type: ignore
        try:
            res = probe.read()
        finally:
            probe._read_fn = orig
    else:
        try:
            res = probe.read()
        except FileNotFoundError as e:
            # no hardware present — surface as 503 with guidance, not 500
            raise HTTPException(status_code=503, detail=str(e))

    try:
        m.thermal_readings_total.labels(tier=settings.tier.value, quality=res.quality).inc()
        m.thermal_value_c.labels(probe_id=res.probe_id).set(res.value)
        m.thermal_latency_ms.observe(res.latency_ms)
    except Exception:
        pass
    health.mark_ok("thermal", latency_ms=res.latency_ms)

    try:
        await sf.enqueue(
            {
                "station_id": res.probe_id,
                "metric": "bearing_temp_c",
                "value": str(res.value),
                "unit": res.unit,
                "quality": res.quality,
                "raw": str(res.raw),
                "tier": settings.tier.value,
                "ts": str(res.timestamp),
            }
        )
    except Exception:
        pass

    return ThermalOut(
        probe_id=res.probe_id,
        raw=res.raw,
        value=res.value,
        unit=res.unit,
        quality=res.quality,  # type: ignore
        latency_ms=res.latency_ms,
        timestamp=res.timestamp,
        tier=settings.tier.value,
        notes=list(res.notes),
    )


# ——— CT ———


@app.post("/infer/ct", response_model=CTOut)
async def infer_ct(body: CTInferIn, claims: dict | None = Depends(require_auth)):
    if not body.samples:
        raise HTTPException(status_code=400, detail="samples empty")
    arr = np.asarray(body.samples, dtype=np.float64)
    try:
        res = analyze_ct(arr, body.sample_rate_hz, mains_hz=body.mains_hz)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    ts = time.time()
    try:
        m.ct_windows_total.labels(tier=settings.tier.value, signature=res.signature).inc()
        m.ct_rms_a.labels(station_id=body.station_id).set(res.rms_a)
    except Exception:
        pass
    health.mark_ok("ct", latency_ms=res.latency_ms)
    try:
        await sf.enqueue(
            {
                "station_id": body.station_id,
                "metric": "current_rms_a",
                "value": str(res.rms_a),
                "unit": "A",
                "signature": res.signature,
                "thd": str(res.thd_percent),
                "tier": settings.tier.value,
                "ts": str(ts),
            }
        )
    except Exception:
        pass
    return CTOut(
        station_id=body.station_id,
        rms_a=res.rms_a,
        peak_a=res.peak_a,
        thd_percent=res.thd_percent,
        fundamental_hz=res.fundamental_hz,
        signature=res.signature,
        harmonics=res.harmonics,
        power_proxy_w=res.power_proxy_w,
        quality=res.quality,
        latency_ms=res.latency_ms,
        tier=settings.tier.value,
        timestamp=ts,
    )


# ——— OTA (secure) ———

_admin_guard = RBAC("plant_admin")


@app.post("/ota/stage")
async def ota_stage(body: OTAStageIn, claims: dict = Depends(_admin_guard)):
    # artifact bytes from b64 if provided
    artifact_bytes = None
    if body.artifact_b64:
        try:
            artifact_bytes = base64.b64decode(body.artifact_b64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"invalid artifact_b64: {e}")
    pkg = OTAPackage(
        version=body.version,
        sha256=body.sha256,
        signature_b64=body.signature_b64,
        artifact_url=body.artifact_url,
        artifact_bytes=artifact_bytes,
        notes=body.notes,
    )
    try:
        out = await ota.stage(pkg, data=artifact_bytes)
    except ValueError as e:
        m.ota_update_total.labels(result="failed").inc()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        m.ota_update_total.labels(result="failed").inc()
        raise HTTPException(status_code=500, detail=str(e))
    m.ota_update_total.labels(result="staged").inc()
    return out


@app.post("/ota/apply")
async def ota_apply(claims: dict = Depends(_admin_guard)):
    try:
        out = ota.apply()
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    # update gauge
    try:
        # clear old version gauge (best-effort)
        m.ota_version_info.labels(version=out["version"]).set(1)
    except Exception:
        pass
    m.ota_update_total.labels(result="applied").inc()
    return out


@app.post("/ota/rollback")
async def ota_rollback(claims: dict = Depends(_admin_guard)):
    try:
        out = ota.rollback()
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    m.ota_update_total.labels(result="rolled_back").inc()
    return out


@app.get("/ota/status")
async def ota_status(claims: dict | None = Depends(require_auth)):
    return ota.status()
