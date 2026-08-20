# DPDP 2023 Memo — one page
- **Personal data:** Only derived telemetry + operator ack metadata; no PII, no biometrics.
- **Residency:** Postgres/Timescale per plant, `data_residency=IN` flag; cloud reasoning only if `plant.allow_cloud=true`.
- **Purpose limitation:** Events used only for correlated alerts + shift reports.
- **Retention:** 90 days hot, 1yr cold, then aggregated.
- **Consent & audit:** Plant admin consent, audit trail, right to erasure via hard delete.
