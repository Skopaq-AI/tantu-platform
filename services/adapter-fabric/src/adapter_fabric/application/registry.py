"""Adapter registry — factory + lifecycle manager."""

from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

from ..domain.models import AdapterConfig, Protocol
from ..adapters.base import BaseAdapter


def _create_adapter(config: AdapterConfig) -> BaseAdapter:
    proto = config.protocol.value if hasattr(config.protocol, "value") else str(config.protocol)
    if proto == Protocol.OPCUA or proto == "opcua":
        from ..adapters.opcua.adapter import OpcUaAdapter

        return OpcUaAdapter(config)
    if proto == Protocol.MODBUS or proto == "modbus":
        from ..adapters.modbus.adapter import ModbusAdapter

        return ModbusAdapter(config)
    if proto == Protocol.MQTT or proto == "mqtt":
        from ..adapters.mqtt.adapter import MqttAdapter

        return MqttAdapter(config)
    if proto == Protocol.MTCONNECT or proto == "mtconnect":
        from ..adapters.mtconnect.adapter import MTConnectAdapter

        return MTConnectAdapter(config)
    if proto == Protocol.ETHERNET_IP or proto == "ethernet_ip":
        from ..adapters.ethernet_ip.adapter import EthernetIpAdapter

        return EthernetIpAdapter(config)
    if proto == Protocol.CAMERA or proto == "camera":
        from ..adapters.camera.adapter import CameraAdapter

        return CameraAdapter(config)
    raise ValueError(f"Unknown protocol: {proto}")


class AdapterRegistry:
    """Holds live adapter instances, manages start/stop, routes readings."""

    def __init__(self) -> None:
        self._adapters: Dict[str, BaseAdapter] = {}
        self._lock = asyncio.Lock()

    async def register(self, config: AdapterConfig) -> BaseAdapter:
        async with self._lock:
            if config.adapter_id in self._adapters:
                # replace: stop old
                old = self._adapters.pop(config.adapter_id)
                try:
                    await old.stop()
                except Exception:
                    pass
            adapter = _create_adapter(config)
            self._adapters[config.adapter_id] = adapter
            if config.enabled:
                await adapter.start()
            return adapter

    async def remove(self, adapter_id: str) -> bool:
        async with self._lock:
            ad = self._adapters.pop(adapter_id, None)
            if ad is None:
                return False
            try:
                await ad.stop()
            except Exception:
                pass
            return True

    async def get(self, adapter_id: str) -> Optional[BaseAdapter]:
        return self._adapters.get(adapter_id)

    def list_ids(self) -> List[str]:
        return list(self._adapters.keys())

    def all_adapters(self) -> List[BaseAdapter]:
        return list(self._adapters.values())

    async def health_all(self) -> List[Dict]:
        out = []
        for ad in self._adapters.values():
            try:
                h = await ad.health()
                out.append(
                    {
                        "adapter_id": h.adapter_id,
                        "protocol": h.protocol,
                        "status": h.status,
                        "last_ok_ts": h.last_ok_ts,
                        "last_error": h.last_error,
                        "message_count": h.message_count,
                        "error_count": h.error_count,
                    }
                )
            except Exception as e:
                out.append(
                    {
                        "adapter_id": ad.adapter_id,
                        "protocol": ad.protocol,
                        "status": "down",
                        "last_error": str(e),
                    }
                )
        return out

    async def stop_all(self) -> None:
        async with self._lock:
            for ad in list(self._adapters.values()):
                try:
                    await ad.stop()
                except Exception:
                    pass

    async def start_all(self) -> None:
        for ad in self._adapters.values():
            try:
                await ad.start()
            except Exception:
                pass
