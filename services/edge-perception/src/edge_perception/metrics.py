"""Prometheus metrics — real counters/histograms, not stubs."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# --- inference ---
gauge_readings_total = Counter(
    "edge_gauge_readings_total", "Gauge reads attempted", ["tier", "quality"]
)
gauge_confidence = Histogram(
    "edge_gauge_confidence", "Gauge confidence", buckets=[0.3, 0.45, 0.6, 0.72, 0.85, 0.95, 1.0]
)
gauge_latency_ms = Histogram(
    "edge_gauge_latency_ms", "Gauge pipeline latency ms", buckets=[5, 10, 18, 25, 40, 80, 150]
)
gauge_value = Gauge("edge_gauge_last_value", "Last gauge value", ["station_id"])

vibration_windows_total = Counter(
    "edge_vibration_windows_total", "Vibration windows analyzed", ["tier", "health"]
)
vibration_rms = Gauge("edge_vibration_rms", "Last RMS", ["station_id"])
vibration_latency_ms = Histogram(
    "edge_vibration_latency_ms", "Vibration FFT latency ms", buckets=[2, 6, 12, 20, 40, 80]
)

thermal_readings_total = Counter(
    "edge_thermal_readings_total", "Thermal reads", ["tier", "quality"]
)
thermal_value_c = Gauge("edge_thermal_value_c", "Last thermal value °C", ["probe_id"])
thermal_latency_ms = Histogram(
    "edge_thermal_latency_ms", "Thermal read latency ms", buckets=[1, 3, 8, 20, 50]
)

ct_windows_total = Counter("edge_ct_windows_total", "CT windows analyzed", ["tier", "signature"])
ct_rms_a = Gauge("edge_ct_rms_a", "CT RMS Amps", ["station_id"])

# --- gateway ---
store_forward_buffered = Gauge("edge_store_forward_buffered", "Store-and-forward buffered entries")
store_forward_enqueued_total = Counter(
    "edge_store_forward_enqueued_total", "Total enqueued", ["dest"]
)
store_forward_drained_total = Counter("edge_store_forward_drained_total", "Total drained to Redis")
store_forward_failed_total = Counter("edge_store_forward_failed_total", "Enqueue failures")

ota_version_info = Gauge("edge_ota_version_info", "OTA current version as label", ["version"])
ota_update_total = Counter("edge_ota_update_total", "OTA updates attempted", ["result"])
