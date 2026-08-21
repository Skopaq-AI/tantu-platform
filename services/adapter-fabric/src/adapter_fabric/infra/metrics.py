"""Prometheus metrics — process + adapter counters."""

from __future__ import annotations

try:
    from prometheus_client import Counter, Gauge, Histogram, CONTENT_TYPE_LATEST, generate_latest  # type: ignore

    _HAS_PROM = True
except Exception:
    _HAS_PROM = False

    class _Noop:
        def inc(self, *a, **kw):
            pass

        def dec(self, *a, **kw):
            pass

        def set(self, *a, **kw):
            pass

        def observe(self, *a, **kw):
            pass

        def labels(self, *a, **kw):
            return self

    CONTENT_TYPE_LATEST = "text/plain"
    Counter = Gauge = Histogram = lambda *a, **kw: _Noop()  # type: ignore

    def generate_latest(*a, **kw):  # type: ignore
        return b"# prometheus_client not installed\n"


if _HAS_PROM:
    READINGS_TOTAL = Counter(
        "adapter_readings_total", "Total readings ingested", ["protocol", "adapter_id", "metric"]
    )
    DEFECTS_TOTAL = Counter(
        "adapter_defects_total", "Defect events emitted", ["protocol", "defect_class"]
    )
    ERRORS_TOTAL = Counter("adapter_errors_total", "Adapter errors", ["protocol", "adapter_id"])
    ADAPTER_UP = Gauge("adapter_up", "Adapter health (1=up, 0=down)", ["protocol", "adapter_id"])
    POLL_LATENCY = Histogram(
        "adapter_poll_duration_seconds", "Poll duration", ["protocol", "adapter_id"]
    )
else:
    READINGS_TOTAL = Counter("x", "x")  # type: ignore
    DEFECTS_TOTAL = Counter("x", "x")  # type: ignore
    ERRORS_TOTAL = Counter("x", "x")  # type: ignore
    ADAPTER_UP = Gauge("x", "x")  # type: ignore
    POLL_LATENCY = Histogram("x", "x")  # type: ignore
