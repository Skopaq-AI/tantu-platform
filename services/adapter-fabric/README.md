# TANTU Adapter Fabric — `services/adapter-fabric`

Real microservice that ingests shopfloor protocols and normalizes to **one canonical schema**. No stubs — every adapter implements real wire logic. Defect events are derived-only; `DefectEvent` has **no image field** by type (raw frames never leave the edge).

```
src/adapter_fabric/
  domain/       — events, models, tag_map (pure)
  adapters/
    opcua/      — asyncua Client, NodeId, DataValue, subscription
    modbus/     — pymodbus AsyncModbusTcpClient, coils/registers, float32 decode
    mqtt/       — paho-mqtt Client, topic map, JSON path, QoS
    mtconnect/  — httpx XML polling, MTConnectStreams parsing, sequence tracking
    ethernet_ip/— pycomm3 LogixDriver + raw EIP/CIP encapsulation (24-byte header, 0x4C Read Tag)
    camera/     — OpenCV gauge needle detection (perspective + HoughCircles + HoughLinesP)
  application/  — registry, normalizer, pipeline (NATS publish, defect detect)
  infra/        — nats, security (JWT HS256), logging (structlog JSON), telemetry (OTEL), metrics
  api/          — FastAPI on :8001, hexagonal
```

## Quick start

```bash
cd services/adapter-fabric
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"   # needs python 3.11; opencv libgl1 on Linux: apt install libgl1
uvicorn adapter_fabric.api.main:app --host 0.0.0.0 --port 8001 --reload
# or
docker build -t adapter-fabric .
docker run -p 8001:8001 -e NATS_URL=nats://host.docker.internal:4222 adapter-fabric
```

Compose (from repo root):

```bash
docker compose up --build
# adapter-fabric is expected on 8001 alongside backend (8000), postgres, redis, nats, qdrant
```

Add to `docker-compose.yml`:

```yaml
  adapter-fabric:
    build: ./services/adapter-fabric
    ports: ["8001:8001"]
    environment:
      NATS_URL: nats://nats:4222
      JWT_PRIVATE_KEY: ${JWT_PRIVATE_KEY:-dev-only-key-replace-in-prod}
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
    depends_on: [nats]
```

## Auth

Same JWT as `backend/src/infra/security.py` — HS256, `JWT_PRIVATE_KEY`.

```bash
# issue a token
curl -s -X POST http://localhost:8001/auth/token \
  -H 'content-type: application/json' \
  -d '{"sub":"operator","plant_id":"plant-demo-01","role":"plant_admin"}' | jq

# use it
TOKEN=$(curl -s -X POST http://localhost:8001/auth/token -H 'content-type: application/json' \
  -d '{"sub":"operator","plant_id":"plant-demo-01","role":"plant_admin"}' | jq -r .access_token)

curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/adapters
```

`plant_admin` bypasses role check; otherwise `authorize(claims, required_role, plant_id)` enforces `role` and `plant_id` binding. Protected: `POST /adapters`, `DELETE /adapters/{id}`, `POST /adapters/{id}/start|stop`.

## Canonical schema

Every adapter emits `NormalizedReading`:

```json
{
  "station_id": "line1-plc01",
  "metric": "pressure_bar",
  "value": 5.31,
  "unit": "bar",
  "timestamp": 1710000000.0,
  "quality": "good",
  "protocol": "modbus",
  "adapter_id": "modbus-1",
  "source_tag": "3:100",
  "raw_value": 53.1
}
```

Published to NATS subject `tantu.telemetry.<metric>` as JSON. Defects derived via `application/normalizer.detect_defect` → `DefectEvent` (no image field) → `tantu.events.defect`.

## Tag-map + compounding

Each adapter has `tags: TagMapping[]`:

- `source_tag` — wire address (`ns=2;i=1001`, `3:100:2`, `factory/line2/pressure`, `spindle_speed`, `MyTag`)
- `metric` + `unit` — canonical name
- `scale` / `offset` — `value = raw*scale + offset`
- `data_type` — `float|int16|uint16|float32|bool|...`
- `compound_formula` + `source_tags: {var: address}` — combine multiple wire tags:

```json
{
  "adapter_id": "opcua-comp-1",
  "protocol": "opcua",
  "station_id": "line1-mixer01",
  "tags": [
    {
      "source_tag": "compound",
      "metric": "pressure_avg",
      "unit": "bar",
      "compound_formula": "(p1 + p2) / 2",
      "source_tags": {"p1": "ns=2;i=1001", "p2": "ns=2;i=1002"}
    }
  ],
  "params": {"endpoint": "opc.tcp://plc:4840"},
  "poll_interval_ms": 500
}
```

Preview a formula without touching PLC:

```bash
curl -s -X POST http://localhost:8001/tag-map/preview \
  -H 'content-type: application/json' \
  -d '{"formula":"(a + b) / 2","variables":{"a":10,"b":20}}' | jq
# {"formula":"(a + b) / 2","variables":{"a":10,"b":20},"value":15.0}
```

Only `ast` arithmetic is allowed (`+ - * / % **`, `abs/min/max/sqrt/...`). No attribute access, no imports.

## Adapters

### OPC-UA (`protocol: opcua`) — asyncua

- `params.endpoint`: `opc.tcp://host:4840` (required for live)
- `params.timeout_s`, `params.use_subscription`
- `tags[].source_tag`: NodeId string, e.g. `ns=2;i=1001`, `ns=2;s=MyVar`
- Real: `asyncua.Client`, `read_data_value`, StatusCode check, exponential backoff reconnect, optional `create_subscription`.

```bash
curl -s -X POST http://localhost:8001/adapters -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{
  "adapter_id":"opcua-1","protocol":"opcua","station_id":"line1-opc01",
  "tags":[{"source_tag":"ns=2;i=1001","metric":"pressure_bar","unit":"bar","scale":1,"offset":0}],
  "params":{"endpoint":"opc.tcp://localhost:4840","timeout_s":5},
  "poll_interval_ms":1000
}' | jq

curl -s -X POST http://localhost:8001/adapters/opcua-1/poll -H "Authorization: Bearer $TOKEN" | jq
```

### Modbus (`modbus`) — pymodbus

- `params.host/port/unit_id/timeout_s`
- `tags[].source_tag`: `"<fc>:<addr>[:<count>]"` where `fc` 1=coil 2=discrete 3=holding 4=input
- `data_type` controls decode: `float32` reads 2 regs big-endian `>f`, `int32`/`uint32` similar, `int16` sign-extends.

```bash
curl -s -X POST http://localhost:8001/adapters -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{
  "adapter_id":"modbus-1","protocol":"modbus","station_id":"line1-plc01",
  "tags":[
    {"source_tag":"3:100:2","metric":"pressure_bar","unit":"bar","data_type":"float32","scale":1},
    {"source_tag":"1:5","metric":"relay_state","unit":"","data_type":"bool"}
  ],
  "params":{"host":"192.168.1.10","port":502,"unit_id":1},
  "poll_interval_ms":500
}' | jq

curl -s -X POST http://localhost:8001/adapters/modbus-1/poll -H "Authorization: Bearer $TOKEN" | jq
```

### MQTT (`mqtt`) — paho-mqtt

- `params.host/port/client_id/username/password/qos/keepalive/use_tls`
- `params.json_path`: dotted path inside JSON payload (e.g. `data.pressure`)
- `tags[].source_tag`: topic filter (supports `+`/`#` wildcards)
- Real: `paho.mqtt.client.Client` loop, `on_message` → `_extract_json_path` → `scale/offset` → NATS.

```bash
curl -s -X POST http://localhost:8001/adapters -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{
  "adapter_id":"mqtt-1","protocol":"mqtt","station_id":"line2-sensor01",
  "tags":[{"source_tag":"factory/line2/pressure","metric":"pressure_bar","unit":"bar","scale":0.1}],
  "params":{"host":"localhost","port":1883,"qos":1,"json_path":"value"},
  "poll_interval_ms":0
}' | jq
# publish from a sensor:
mosquitto_pub -h localhost -t factory/line2/pressure -m "{\"value\": 85}"
curl -s -X POST http://localhost:8001/adapters/mqtt-1/poll | jq
```

### MTConnect (`mtconnect`) — httpx xml

- `params.base_url`: agent `http://host:5000`
- `params.device`, `params.use_sample`, `params.timeout_s`, `params.path`
- `tags[].source_tag`: `dataItemId` (e.g. `spindle_speed`, `avail`)
- Real: `httpx.AsyncClient`, `/current` + `/sample?from=nextSequence`, `xml.etree.ElementTree`, `instanceId` tracking.

```bash
curl -s -X POST http://localhost:8001/adapters -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{
  "adapter_id":"mtc-1","protocol":"mtconnect","station_id":"line1-cnc01",
  "tags":[{"source_tag":"spindle_speed","metric":"spindle_speed","unit":"rpm"}],
  "params":{"base_url":"http://mtconnect-agent:5000","timeout_s":5},
  "poll_interval_ms":2000
}' | jq

curl -s -X POST "http://localhost:8001/adapters/mtc-1/poll" -H "Authorization: Bearer $TOKEN" | jq
```

### EtherNet/IP (`ethernet_ip`) — pycomm3 + real CIP/EIP frame

- `params.host/port/slot/timeout_s/use_pycomm3`, `params.data_type_map: {tag: REAL|DINT|...}`
- `tags[].source_tag`: `MyTag`, `MyTag[0]`, or `class:1,instance:1,attr:1`
- Real frame: 24-byte EIP header (`<HHI I 8s I` little-endian), CIP `0x4C Read Tag` with EPATH symbol `0x91`, `SendRRData 0x6F` + CPF. `pycomm3.LogixDriver` preferred; raw socket fallback verified by byte-level tests.

```bash
curl -s -X POST http://localhost:8001/adapters -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{
  "adapter_id":"eip-1","protocol":"ethernet_ip","station_id":"line1-plc01",
  "tags":[{"source_tag":"MyTag","metric":"pressure_bar","unit":"bar","data_type":"REAL"}],
  "params":{"host":"192.168.1.20","slot":0,"data_type_map":{"MyTag":"REAL"}},
  "poll_interval_ms":500
}' | jq

# offline still proves frame building:
python -c "from adapter_fabric.adapters.ethernet_ip import build_cip_read_tag_request, build_send_rr_data, parse_eip_header; f=build_send_rr_data(0xABCD, build_cip_read_tag_request('MyTag')); print(parse_eip_header(f))"
```

### Camera (`camera`) — OpenCV gauge needle

Frames never leave the adapter. Pipeline: `perspective_correct` (4-point homography) → `HoughCircles` → `Canny` + `HoughLinesP` through center → angle → `GaugeCalibration.angle_to_value`.

- `params.image_path` / `video_path` / `rtsp_url` — source
- `params.calibration: {min_angle, max_angle, min_value, max_value, angle_offset}`
- `params.src_points: [[x,y]*4]` — optional manual perspective
- `params.gauge: {dp, min_dist, param1, param2, radius_range:[min,max], dst_size}`

```bash
curl -s -X POST http://localhost:8001/adapters -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{
  "adapter_id":"cam-1","protocol":"camera","station_id":"line1-gauge01",
  "tags":[{"source_tag":"camera","metric":"gauge_value","unit":"bar"}],
  "params":{
    "image_path":"/data/gauge.jpg",
    "calibration":{"min_angle":-135,"max_angle":135,"min_value":0,"max_value":100},
    "gauge":{"dp":1.2,"min_dist":80,"param1":100,"param2":30,"radius_range":[40,200]}
  },
  "poll_interval_ms":1000
}' | jq

curl -s -X POST http://localhost:8001/adapters/cam-1/poll -H "Authorization: Bearer $TOKEN" | jq
# test helper without camera:
python -c "
from adapter_fabric.adapters.camera import generate_synthetic_gauge_image, analyze_gauge_image, GaugeCalibration
cal=GaugeCalibration(-135,135,0,100); img=generate_synthetic_gauge_image(60, calibration=cal, noise=False)
print(analyze_gauge_image(img, cal))
"
```

`DefectEvent` is derived only — the image is dropped after `analyze_gauge_image`; `tests/test_camera.py` asserts the field does not exist.

## HTTP API

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | no | service + per-adapter health, `nats_connected` |
| GET | `/metrics` | no | Prometheus text |
| GET | `/info` | no | canonical schema + protocol list |
| POST | `/auth/token` | no | issue JWT (demo) |
| POST | `/adapters` | Bearer | register/upsert adapter |
| GET | `/adapters` | optional | list adapters + health |
| GET | `/adapters/{id}` | no | get one adapter |
| DELETE | `/adapters/{id}` | Bearer | remove adapter |
| POST | `/adapters/{id}/start` | Bearer | start adapter poll loop |
| POST | `/adapters/{id}/stop` | Bearer | stop adapter |
| POST | `/adapters/{id}/poll` | optional | poll once → `NormalizedReading[]` |
| GET | `/readings` | optional | poll all adapters |
| POST | `/ingest` | optional | ingest one reading (gateway) |
| GET | `/events` | no | synthetic DefectEvents demo |
| POST | `/tag-map/preview` | no | compound formula preview |
| GET | `/openapi.json` | no | OpenAPI 3.1 |

OpenAPI is served at `GET /openapi.json` and `GET /docs` (Swagger).

## cURL cookbook (end-to-end)

```bash
BASE=http://localhost:8001
TOKEN=$(curl -s -X POST $BASE/auth/token -H 'content-type: application/json' \
  -d '{"sub":"op","plant_id":"plant-demo-01","role":"plant_admin"}' | jq -r .access_token)
AUTH="Authorization: Bearer $TOKEN"

# health + metrics
curl -s $BASE/health | jq
curl -s $BASE/metrics | head

# register 3 adapters and poll
curl -s -X POST $BASE/adapters -H "$AUTH" -H 'content-type: application/json' -d '{
  "adapter_id":"opcua-1","protocol":"opcua","station_id":"line1-opc01",
  "tags":[{"source_tag":"ns=2;i=1001","metric":"pressure_bar","unit":"bar"}],
  "params":{"endpoint":"opc.tcp://localhost:4840"},"poll_interval_ms":0
}' | jq
curl -s -X POST $BASE/adapters -H "$AUTH" -H 'content-type: application/json' -d '{
  "adapter_id":"modbus-1","protocol":"modbus","station_id":"line1-plc01",
  "tags":[{"source_tag":"3:100:2","metric":"vibration_rms","unit":"mm/s","data_type":"float32"}],
  "params":{"host":"127.0.0.1","port":5020},"poll_interval_ms":0
}' | jq
curl -s -X POST $BASE/adapters -H "$AUTH" -H 'content-type: application/json' -d '{
  "adapter_id":"cam-1","protocol":"camera","station_id":"line1-gauge01",
  "tags":[{"source_tag":"camera","metric":"gauge_value","unit":"psi"}],
  "params":{"calibration":{"min_angle":-135,"max_angle":135,"min_value":0,"max_value":100}},"poll_interval_ms":0
}' | jq

curl -s $BASE/adapters -H "$AUTH" | jq
curl -s -X POST $BASE/adapters/cam-1/poll -H "$AUTH" | jq
curl -s $BASE/readings | jq
curl -s $BASE/events?limit=3 | jq

# tag compounding preview
curl -s -X POST $BASE/tag-map/preview -H 'content-type: application/json' \
  -d '{"formula":"sqrt(a*a + b*b)","variables":{"a":3,"b":4}}' | jq

# direct ingest (gateway)
curl -s -X POST $BASE/ingest -H 'content-type: application/json' \
  -d '{"station_id":"line1-s01","metric":"pressure_bar","value":9.2,"unit":"bar","protocol":"mqtt"}' | jq

# NATS: readings are on tantu.telemetry.* and defects on tantu.events.defect
nats sub "tantu.>"
```

## Architecture

- **Hexagonal + Clean**: `domain` has no infra imports. `adapters/*` depend inward on `domain`. `application` orchestrates `registry` + `pipeline`. `api` is a thin driving adapter.
- **Async throughout**: `BaseAdapter.start/stop/poll_once`, `httpx.AsyncClient`, `asyncua.Client`, `AsyncModbusTcpClient`, pipeline `asyncio.Queue` fan-in.
- **Structured logging**: `structlog` JSON, `adapter_id/protocol/metric` bound in context.
- **OpenTelemetry**: `infra/telemetry.py` — OTLP if `OTEL_EXPORTER_OTLP_ENDPOINT` set, else console. Traces wrap poll latency.
- **Health / metrics**: `GET /health` per-adapter `status/last_ok_ts/last_error/message_count`; `GET /metrics` via `prometheus_client` (`adapter_readings_total`, `adapter_defects_total`, `adapter_errors_total`, `adapter_up`, `adapter_poll_duration_seconds`).
- **NATS**: `nats-py`; JetStream if available, else core `publish`. Publishes `NormalizedReading` → `tantu.telemetry.<metric>` and `DefectEvent` → `tantu.events.defect`. In-memory buffer fallback for tests/offline.
- **Security**: JWT HS256 (`JWT_PRIVATE_KEY`), `require_auth` dependency, RBAC+ABAC (`role`, `plant_id`). `frames_never_leave` invariant enforced by type.

## Tests

```bash
pytest -q
pytest tests/test_camera.py -q          # gauge round-trip
pytest tests/test_adapters.py -q        # Modbus decode, MTConnect XML, MQTT inject, EIP frame
pytest tests/test_api.py -q             # FastAPI + auth + tag-map preview
```

## Environment

| Var | Default | Purpose |
|---|---|---|
| `NATS_URL` | `nats://localhost:4222` | NATS server |
| `JWT_PRIVATE_KEY` | `dev-only-key-replace-in-prod` | HS256 secret |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | _(empty)_ | e.g. `http://otel-collector:4317` |
| `LOG_LEVEL` | `INFO` | structlog level |

## License

Proprietary — TANTU.
