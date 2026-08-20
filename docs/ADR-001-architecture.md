# ADR-001 — Hybrid edge/cloud, frames never leave
- **Decision:** Raw frames on-prem only (<40ms edge), derived events to cloud if permitted. Enforced by type (DefectEvent has no image field).
- **Consequence:** DPDP/ITAR friendly, SOC2-ready, air-gapped via Nemotron SLM path.
- **Alternatives rejected:** Gemini-only (lock-in), NVIDIA-only (no vernacular RAG).
