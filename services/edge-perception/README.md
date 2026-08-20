# Edge Perception — TANTU

Tiered, offline-first edge inference microservice. **FastAPI on :8002**. Real inference — no stubs.

| Modality | Pipeline | Output |
|---|---|---|
| Gauge reading (camera-as-adapter) | OpenCV `adaptiveThreshold` + `HoughCircles` + `Canny`/`HoughLinesP` → needle angle → value | `value`, `angle_deg`, `confidence`, `quality` |
| Vibration (accelerometer window) | `numpy`/`scipy` FFT (`hann`, `find_peaks`, band energy, kurtosis) | `rms`, `peak_freqs`, `crest`, `health` |
| Thermal (1-Wire DS18B20) | `w1_slave` parse + **real** offset/scale + polynomial + 2-point calibration | `value °C`, `quality`, `notes` |
| CT clamp | FFT harmonic signature + THD → load class | `rms_A`, `thd%`, `signature` |

Frames never leave the plant — only `DefectEvent`/`TelemetryReading`-shaped derived values are forwarded.

## Quick start

```bash
cd tantu-platform/services/edge-perception
pip install -e ".[dev]"
uvicorn edge_perception.api.main:app --host 0.0.0.0 --port 8002 --reload
# health
curl http://localhost:8002/health | jq
# gauge inference (send base64 JPEG)
curl -X POST http://localhost:8002/infer/gauge -H 'content-type: application/json' \
  -d '{"station_id":"line2-gauge3","image_b64":"<...jpeg base64...>"}' | jq
# vibration
curl -X POST http://localhost:8002/infer/vibration -H 'content-type: application/json' \
  -d '{"station_id":"motor-01","samples":[...1024 floats...],"sample_rate_hz":1000}' | jq
# thermal (injected raw, no hardware)
curl -X POST http://localhost:8002/infer/thermal -H 'content-type: application/json' \
  -d '{"probe_id":"bearing-01","raw":67.3}' | jq
# CT
curl -X POST http://localhost:8002/infer/ct -H 'content-type: application/json' \
  -d '{"station_id":"panel-ct1","samples":[...],"sample_rate_hz":2000}' | jq
# prometheus
curl http://localhost:8002/metrics
```

Docker:
```bash
docker build -t tantu/edge-perception:0.1.0 .
docker run --rm -p 8002:8002 -e EDGE_TIER=pi5_hailo -e REDIS_URL=redis://host.docker.internal:6379/0 tantu/edge-perception:0.1.0
```

## Tier detection (env `EDGE_TIER`)

| Value | Tier | Accel | Gauge budget | FFT budget |
|---|---|---|---|---|
| `pi5_hailo`, `pi5`, `hailo` | Pi 5 + Hailo-8L (8 TOPS) | Hailo-8L | 40 ms | 20 ms |
| `orin_nano`, `orin` | Jetson Orin Nano (40 TOPS) | Ampere 1024-CUDA | 25 ms | 12 ms |
| `thor`, `jetson_thor` | Jetson Thor (2070 TFLOPS) | Blackwell 2070 | 12 ms | 6 ms |

Falls back to `/proc/device-tree/model` heuristics, then to `pi5_hailo`. Override with `EDGE_TIER=orin_nano`.

Latency beyond `1.6×` budget marks the component `degraded` in `/health` (no failure — still returns values).

## Offline-first / store-and-forward

- Every inference result is `XADD`'d to Redis Stream `tantu:edge:readings` (configurable `REDIS_URL`/`REDIS_STREAM`).
- If Redis is unreachable, entries buffer in a bounded in-memory queue (`REDIS_MAX_BUFFER`, default 10 000; oldest dropped on overflow, `dropped` counter exposed).
- Background drain every 2 s pushes the buffer to Redis when it recovers. `enqueue()` never raises — inference never blocks on the network.
- Health at `GET /health` exposes `store_forward:{redis_ok, buffered, dropped, enqueued_total, drained_total}`.
- Prometheus: `edge_store_forward_buffered`, `edge_store_forward_enqueued_total`, `edge_store_forward_drained_total`, `edge_store_forward_failed_total`.

## Thermal calibration (real)

- `ThermalConfig` holds `offset`, `scale`, optional `c2`/`c3` polynomial trim. `calibrated = (raw+offset)*scale + c2*raw² + c3*raw³`
- Two-point: `POST /infer/thermal {"calibrate_two_point":{"raw_low":...,"ref_low":...,"raw_high":...,"ref_high":...}}` computes scale/offset from two reference points and persists to the probe.
- Slew guard (`max_rate_c_per_s`, default 20 °C/s) and range guard (`min_valid`/`max_valid`) downgrade `quality` to `uncertain`/`bad`.
- 1-Wire live read: parses `/sys/bus/w1/devices/<probe_id>/w1_slave` (`t=` field). Inject `raw` in the request body to run without hardware (used by tests / synthetic).

## OTA (secure, stub transport + real verification)

- `POST /ota/stage` (RBAC `plant_admin`): supply `version` (semver, monotonic — must be newer than current), `sha256`, optional `signature_b64`, and either `artifact_b64` (base64 bytes) or `artifact_url` (fetched with `httpx`).
- Verifies `sha256`, then signature: Ed25519 via `cryptography` if `OTA_PUBLIC_KEY_PATH` points to a PEM/raw key, else HMAC-SHA256 via `JWT_SECRET`. Rejects on mismatch, wrong version, or bad sha. No verifier configured + no signature → dev-mode allow; with signature present but no verifier → fail closed.
- `POST /ota/apply` flips `current_version` (persists to `/tmp/tantu-edge-ota.json`), `POST /ota/rollback` restores `previous_version`. `GET /ota/status` reports state machine (`idle→downloading→verifying→staging→ready→applied/failed`).

Auth: issue via `from edge_perception.security.auth import issue_jwt; issue_jwt("user","plant-01","plant_admin")`, send `Authorization: Bearer <jwt>`.

## JWT auth and metrics

- `Authorization: Bearer <jwt>` — HS256 (`JWT_SECRET` or `JWT_PRIVATE_KEY`) / RS256 auto-detected. Infer endpoints allow anonymous when no token (edge convenience); OTA requires `plant_admin`.
- Prometheus on `GET /metrics`: gauge/vibration/thermal/CT counters & histograms + store-forward + OTA version.

## Layout

```
src/edge_perception/
  config.py                 tier detection + Settings
  inference/
    gauge.py                adaptiveThreshold + HoughCircles + needle angle
    vibration.py            FFT + find_peaks + band energy + kurtosis
    thermal.py              1-Wire + real calibration
    ct_clamp.py             THD + harmonic signature
  gateway/
    store_forward.py        Redis Stream + offline buffer
    health.py               component health
    tier.py
  ota/updater.py            sha256 + signature + semver monotonic
  security/auth.py          JWT + RBAC
  metrics.py                prometheus_client
  api/
    main.py                 FastAPI on 8002 (lifespan, CORS, all routes)
    schemas.py
tests/
  test_gauge.py             synthetic gauge images (clean / glare / noise)
  test_vibration.py         synthetic sine fixtures + kurtosis
  test_thermal.py           two-point + slew/range guards
  test_ct.py                mains harmonics
  test_tier_and_store.py    tier mapping + InMemoryStore + OTA
  test_api.py               /health /metrics /infer/* e2e
```

## Tests

```bash
pytest -q
pytest tests/test_gauge.py -v
pytest tests/test_api.py -v
```

## Env

| Var | Default | Notes |
|---|---|---|
| `EDGE_TIER` | `pi5_hailo` | tier select |
| `REDIS_URL` | `redis://localhost:6379/0` | stream backend |
| `REDIS_STREAM` | `tantu:edge:readings` | stream key |
| `REDIS_MAX_BUFFER` | `10000` | in-mem cap |
| `JWT_SECRET` / `JWT_PRIVATE_KEY` | `dev-only-key…` | HMAC/OTA secret |
| `OTA_PUBLIC_KEY_PATH` | `` | Ed25519 PEM path |
| `OTA_CURRENT_VERSION` | `0.1.0` | boot version |

## Contract — frames never leave

`POST /infer/gauge` accepts `image_b64` but the response and the stream entry contain only derived numerics (`value`, `confidence`, `angle_deg`, `quality`). The raw image is never forwarded, never logged, never stored — enforced by type (`GaugeResult` has no image field) and by the store-forward payload shape.
