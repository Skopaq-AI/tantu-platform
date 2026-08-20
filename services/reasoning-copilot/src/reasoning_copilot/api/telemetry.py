"""OpenTelemetry — FastAPI instrumentation + OTLP export."""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def init_telemetry(app, service_name: str = "reasoning-copilot"):
    try:
        from opentelemetry import trace  # type: ignore
        from opentelemetry.sdk.trace import TracerProvider  # type: ignore
        from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore
        from opentelemetry.sdk.resources import Resource  # type: ignore
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # type: ignore

        from ..config import settings

        resource = Resource.create({"service.name": service_name, "service.version": settings.service_version})
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)

        # OTLP exporter if endpoint configured
        if settings.otel_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # type: ignore

                exporter = OTLPSpanExporter(endpoint=settings.otel_endpoint)
                provider.add_span_processor(BatchSpanProcessor(exporter))
                log.info("OTEL: OTLP exporter -> %s", settings.otel_endpoint)
            except Exception as e:
                log.warning("OTEL OTLP exporter failed: %s", e)
        else:
            log.info("OTEL: no OTLP endpoint — traces in-memory only")

        FastAPIInstrumentor.instrument_app(app)
        log.info("OTEL: instrumented FastAPI %s", service_name)
    except Exception as e:
        log.warning("OTEL init skipped: %s", e)
