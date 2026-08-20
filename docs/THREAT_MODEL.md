# Threat Model (STRIDE-lite)
| Asset | Threat | Mitigation |
|---|---|---|
| DefectEvent | Tamper | mTLS edge→backend, NATS signed, audit log |
| JWT | Replay | RS256, short exp, Redis denylist, plant_id ABAC |
| Gauge image | Exfil | Never leaves edge — schema impossible, DLP |
| OTA | Supply chain | Signed images, SBOM, cosign, pinned deps |
| Voice | Spoof | Speaker ACK is not auth; operator ACK is telemetry only |
