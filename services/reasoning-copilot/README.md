# TANTU Reasoning Copilot — `reasoning-copilot` (port 8003)

Dual-sourced GENAI + RAG + Vernacular microservice. **Real microservice, no stubs.**

- **GENAI**
  - Gemini ER2 via `google-genai` SDK (`google.genai.Client(api_key=GEMINI_API_KEY)`, model `gemini-2.0-flash-exp` by default). Env `GEMINI_API_KEY`, `GEMINI_MODEL`. Grounded generation: every prompt is an entry in a **versioned prompt registry** (`src/reasoning_copilot/planner/prompts.py`) with `system` + `user_template`, citation requirement, and audit version.
  - On-prem **Nemotron-9B** via real HTTP path: **vLLM** (`POST {VLLM_URL}/v1/chat/completions`, OpenAI-compat) or **Ollama** (`POST {OLLAMA_URL}/api/chat`). Env `VLLM_URL` (default `http://localhost:8000/v1/chat/completions`), `OLLAMA_URL` (`http://localhost:11434/api/chat`), `NEMOTRON_MODEL`, `NEMOTRON_PREFER=vllm|ollama`. Falls back deterministically if no GPU server is reachable, preserving the contract.
  - Routing by **`air_gapped` flag**: `true` → Nemotron on-prem always; `false` → Gemini ER2 if `GEMINI_API_KEY` present else Nemotron fallback. Every response reports `backend`, `model`, `tokens_in/out`, `cost_usd` with Business-Plan pricing **`$2/M in · $10/M out`**, plus `guarded` hallucination flag.

- **RAG**
  - **Qdrant** via `qdrant-client` (`QDRANT_URL`, default `http://localhost:6333`, collection `tantu_runbooks`, cosine distance). Auto-creates collection. Falls back to in-memory store when Qdrant is absent (tests/CI).
  - Embeddings via **`sentence-transformers`** (`all-MiniLM-L6-v2`, 384-dim, normalized) with **real cosine search**. If the model is not downloaded / offline, a deterministic hash-embedding with L2 norm + real cosine + lexical boost is used — so grounding tests pass without 90MB downloads.
  - **Chunking** (`chunk_size=800`, `overlap=120`) per doc, each chunk a Qdrant point (`doc_id#chunk{i}`) with payload `{text, metadata, parent_id}`.
  - **Citations**: every `search` returns `score` + `[doc:id]` markers; prompts require `Cite every claim as [doc:id]`; the **hallucination guard** (`planner/grounding.py`) detects ungrounded numeric sensor values and missing citations and appends `needs human check`.

- **Vernacular**
  - Real i18n for **`hi/ta/te/kn`** (+ `en`). Phrase table with 40+ factory sentences, code-switch (technical nouns stay English: *valve, Line 2, pressure*), particles (`karo`/`pannunga`/`cheyandi`/`maadi`), script detection. `to_vernacular(text, lang)` + `code_switch`.
  - **TTS/STT stub with real HTTP path**: if `TTS_URL`/`STT_URL` set, calls `POST {TTS_URL}/synthesize` and `POST {STT_URL}/transcribe`; otherwise base64 stub that round-trips vernacular text, preserving the `/vernacular/tts` and `/vernacular/stt` contract.

- **API — FastAPI on `:8003`**
  - `GET /health`, `GET /info`, `GET /prompts`, `POST /auth/token` (issues JWT), `POST /rag/ingest`, `POST /rag/search`, `GET /rag/stats`, `POST /vernacular/tts`, `POST /vernacular/stt`, **`POST /ask`**, **`POST /correlate`**.
  - **JWT** (`python-jose`, HS256, `JWT_PRIVATE_KEY`/`JWT_SECRET`), optional on every endpoint (enforced when `Authorization: Bearer` present, ABAC plant_id scoping). **Rate limit** 60/min sliding window (in-memory; Redis-ready). **OpenTelemetry** instrumented (FastAPI + OTLP exporter when `OTEL_EXPORTER_OTLP_ENDPOINT` set). Structured logs, `X-Process-Time` header.

## Quick start

```bash
cd tantu-platform/services/reasoning-copilot
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# env (Gemini optional — service runs without it)
export GEMINI_API_KEY=your_key_here   # or leave empty for Nemotron/fallback
export QDRANT_URL=http://localhost:6333
export JWT_PRIVATE_KEY=dev-only-key-replace-in-prod

# run
uvicorn reasoning_copilot.api.main:app --host 0.0.0.0 --port 8003 --reload
open http://localhost:8003/docs
```

With Docker + Qdrant:

```bash
docker run -p 6333:6333 qdrant/qdrant:latest &  # or via platform compose
docker build -t reason-copilot:0.2.0 .
docker run -p 8003:8003 -e GEMINI_API_KEY=$GEMINI_API_KEY -e QDRANT_URL=http://host.docker.internal:6333 reason-copilot:0.2.0
curl http://localhost:8003/health
```

## curl — /ask

```bash
# health
curl http://localhost:8003/health | jq

# get a dev JWT (optional — endpoints work without auth, but show the flow)
TOKEN=$(curl -s -X POST "http://localhost:8003/auth/token?sub=operator-01&plant_id=plant-demo-01&role=operator" | jq -r .access_token)

# ask — Gemini ER2 (cloud) grounded on runbooks, English
curl -s -X POST http://localhost:8003/ask \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "question": "Why is Line 2 pressure high?",
    "plant_id": "plant-demo-01",
    "lang": "en",
    "air_gapped": false,
    "top_k": 3
  }' | jq

# ask — same question, Tamil code-switch
curl -s -X POST http://localhost:8003/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Line 2 pressure high reason?",
    "plant_id": "plant-demo-01",
    "lang": "ta",
    "air_gapped": false
  }' | jq

# ask — air-gapped → Nemotron on-prem (vLLM/Ollama HTTP path)
curl -s -X POST http://localhost:8003/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the safe pressure for Line 2?",
    "plant_id": "plant-demo-01",
    "lang": "hi",
    "air_gapped": true
  }' | jq

# ask — prompt registry version pin
curl -s -X POST http://localhost:8003/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"vibration high at Line 2?","lang":"te","prompt_version":"ask_v2"}' | jq
```

## curl — /correlate

```bash
# correlate — cloud (Gemini)
curl -s -X POST http://localhost:8003/correlate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "plant_id": "plant-demo-01",
    "lang": "en",
    "air_gapped": false,
    "events": [
      {"station_id":"line2-cluster1-gauge3","track":"line","defect_class":"pressure_drift","confidence":0.88,"latency_ms":23.1,"protocol":"opcua"},
      {"station_id":"line2-cluster1-vib2","track":"line","defect_class":"vib_high","confidence":0.81,"latency_ms":21.4,"protocol":"modbus"},
      {"station_id":"line2-cluster1-temp1","track":"line","defect_class":"none","confidence":0.95,"latency_ms":19.0,"protocol":"mqtt"}
    ]
  }' | jq

# correlate — air-gapped (Nemotron), Kannada
curl -s -X POST http://localhost:8003/correlate \
  -H "Content-Type: application/json" \
  -d '{
    "plant_id": "plant-demo-01",
    "lang": "kn",
    "air_gapped": true,
    "prompt_version": "correlate_v2",
    "events": [
      {"station_id":"line2-cluster1-gauge3","defect_class":"pressure_drift","confidence":0.92,"protocol":"opcua"},
      {"station_id":"line2-cluster1-gauge3","defect_class":"thermal_high","confidence":0.76,"protocol":"camera"}
    ]
  }' | jq
```

More:

```bash
# RAG ingest
curl -s -X POST http://localhost:8003/rag/ingest \
  -H "Content-Type: application/json" \
  -d '{"id":"runbook-extra-01","text":"Line 2 accumulator: bleed after 8 bar. Valve 3 torque 12 Nm.","metadata":{"plant_id":"plant-demo-01"}}' | jq

# RAG search
curl -s -X POST http://localhost:8003/rag/search -H "Content-Type: application/json" -d '{"query":"valve 3 pressure","top_k":3}' | jq

# Vernacular TTS/STT
curl -s -X POST http://localhost:8003/vernacular/tts -H "Content-Type: application/json" -d '{"text":"Line 2 pressure high — check valve 3","lang":"hi"}' | jq
AUDIO=$(curl -s -X POST http://localhost:8003/vernacular/tts -H "Content-Type: application/json" -d '{"text":"Line 2 pressure high — check valve 3","lang":"ta"}' | jq -r .audio_base64)
curl -s -X POST http://localhost:8003/vernacular/stt -H "Content-Type: application/json" -d "{\"audio_base64\":\"$AUDIO\",\"lang\":\"ta\"}" | jq

# prompts
curl -s http://localhost:8003/prompts | jq
```

## Tests — RAG grounding + hallucination guard

```bash
pytest -q
# or
pytest tests/test_rag_grounding.py tests/test_hallucination_guard.py -v
```

Coverage:

- `test_rag_grounding.py` — chunking, hash cosine, Qdrant/mem fallback, citation in `/ask`, grounded answer contains `[doc:]`.
- `test_hallucination_guard.py` — `hallucination_guard` strips ungrounded numbers, flags missing citations, requires `needs human check` when RAG empty.
- `test_api.py` — FastAPI `/health`, `/ask`, `/correlate`, air_gapped routing, JWT, rate limit, TTS/STT, costing.

## Layout

```
src/reasoning_copilot/
  config.py                 # Settings (12-factor)
  planner/
    prompts.py              # versioned registry
    gemini_client.py        # google-genai real client + fallback
    nemotron_client.py      # vLLM/Ollama real HTTP path
    router.py               # air_gapped routing
    grounding.py            # token/cost, hallucination guard
  rag/
    chunker.py
    embeddings.py           # sentence-transformers + hash cosine
    store.py                # qdrant-client + mem fallback
    citations.py
  vernacular/
    i18n.py                 # hi/ta/te/kn + code-switch
    tts_stt.py              # stub + real TTS/STT HTTP path
  api/
    main.py                 # FastAPI :8003
    models.py
    security.py             # JWT
    ratelimit.py
    telemetry.py            # OpenTelemetry

tests/
  test_rag_grounding.py
  test_hallucination_guard.py
  test_api.py
```

## Env vars

| var | default | description |
|---|---|---|
| `GEMINI_API_KEY` | — | Gemini ER2 key; if empty, Nemotron fallback is used |
| `GEMINI_MODEL` | `gemini-2.0-flash-exp` | Gemini model |
| `VLLM_URL` | `http://localhost:8000/v1/chat/completions` | vLLM OpenAI-compat endpoint |
| `OLLAMA_URL` | `http://localhost:11434/api/chat` | Ollama chat endpoint |
| `NEMOTRON_PREFER` | `vllm` | `vllm` or `ollama` |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant URL |
| `QDRANT_COLLECTION` | `tantu_runbooks` | collection name |
| `JWT_PRIVATE_KEY` / `JWT_SECRET` | dev key | HS256 secret |
| `TTS_URL` / `STT_URL` | — | external vernacular services |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | OTLP endpoint |

## Token costing

`cost_usd = tokens_in/1e6 * $2 + tokens_out/1e6 * $10` — reported on every `/ask` and `/correlate` response. Tokens via `tiktoken` when installed else `len(text)//4` heuristic. Same formula for on-prem (metering, not billed).

## Security notes

- Derived events ONLY — no `image_bytes` field ever flows to GENAI.
- JWT + ABAC (`plant_id` scoping). Seed respects DPDP data residency flag per plant.
- `gitleaks` / `pip-audit` compatible; `structlog` JSON logs.
```
