"""OpenTelemetry wiring — no-op if endpoint not configured."""

from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

try:
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    _HAS_OTLP = True
except Exception:
    _HAS_OTLP = False

SERVICE_NAME = "adapter-fabric"


def configure_tracing() -> trace.Tracer:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    resource = Resource.create({"service.name": SERVICE_NAME})
    provider = TracerProvider(resource=resource)

    if endpoint and _HAS_OTLP:
        processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces"))
    else:
        processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    return trace.get_tracer(SERVICE_NAME)


def get_tracer(name: str = SERVICE_NAME) -> trace.Tracer:
    try:
        return trace.get_tracer(name)
    except Exception:
        # fallback if provider not set yet
        return trace.get_tracer(name)
