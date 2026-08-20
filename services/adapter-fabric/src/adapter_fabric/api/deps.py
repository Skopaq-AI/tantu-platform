"""Shared dependencies."""
from ..application.registry import AdapterRegistry
from ..infra.nats import NatsPublisher, get_publisher

_registry: AdapterRegistry | None = None


def get_registry() -> AdapterRegistry:
    global _registry
    if _registry is None:
        _registry = AdapterRegistry()
    return _registry


def set_registry(r: AdapterRegistry) -> None:
    global _registry
    _registry = r


def get_nats() -> NatsPublisher:
    return get_publisher()
