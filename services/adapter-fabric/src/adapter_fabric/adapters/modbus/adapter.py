"""Modbus adapter — real pymodbus AsyncModbusTcpClient.

Supports coils, discrete inputs, holding registers, input registers.
Handles scale/offset, data_type coercion, float32 from two registers,
and tag-map compounding.
"""
from __future__ import annotations

import asyncio
import struct
import time
from typing import Any, Dict, List, Optional

from ...domain.events import Quality, NormalizedReading
from ...domain.models import AdapterConfig
from ...domain.tag_map import normalize_raw_value, apply_tag_mapping, compound
from ..base import BaseAdapter

try:
    from pymodbus.client import AsyncModbusTcpClient  # type: ignore
    from pymodbus.exceptions import ModbusException  # type: ignore

    _HAS_PYMODBUS = True
except Exception:  # pragma: no cover
    _HAS_PYMODBUS = False
    AsyncModbusTcpClient = object  # type: ignore


# Function code mapping for clarity
# 1: read_coils, 2: read_discrete_inputs, 3: read_holding_registers, 4: read_input_registers


def _decode_registers(registers: List[int], data_type: str) -> float:
    """Decode one or more 16-bit registers to float/int per data_type."""
    dt = data_type.lower()
    if not registers:
        raise ValueError("No registers")
    if dt == "float32":
        # two registers → big-endian float32 (Modbus default big-endian)
        if len(registers) < 2:
            raise ValueError("float32 needs 2 registers")
        # pymodbus returns list of uint16 in network/big-endian order
        raw = struct.pack(">HH", registers[0], registers[1])
        return struct.unpack(">f", raw)[0]
    if dt == "int32":
        if len(registers) < 2:
            raise ValueError("int32 needs 2 registers")
        raw = struct.pack(">HH", registers[0], registers[1])
        return float(struct.unpack(">i", raw)[0])
    if dt == "uint32":
        if len(registers) < 2:
            raise ValueError("uint32 needs 2 registers")
        raw = struct.pack(">HH", registers[0], registers[1])
        return float(struct.unpack(">I", raw)[0])
    if dt == "int16":
        v = registers[0]
        if v & 0x8000:
            v = v - 0x10000
        return float(v)
    if dt == "uint16":
        return float(registers[0] & 0xFFFF)
    # bool / coil handled elsewhere
    return float(registers[0])


class ModbusAdapter(BaseAdapter):
    """Modbus TCP adapter.

    config.params:
      host: str (default 127.0.0.1)
      port: int (default 502)
      unit_id: int (default 1)
      timeout_s: float (default 3)

    Tag source_tag format: "<fc>:<address>[:<count>]"
      fc: 1=coil, 2=discrete, 3=holding, 4=input
      address: zero-based register/coil address
      count: register count (default 1, 2 for float32/int32)

      Examples:
        "3:100"        -> holding reg 100, 1 reg
        "3:100:2"      -> holding regs 100-101, 2 regs (float32)
        "1:5"          -> coil 5
        "4:0:2"        -> input regs 0-1

    Alternatively params may contain "register_map" dict.
    """

    def __init__(self, config: AdapterConfig) -> None:
        super().__init__(config)
        self._client: Optional[Any] = None
        self._connected = False

    async def _on_start(self) -> None:
        if not _HAS_PYMODBUS:
            self._status = "degraded"
            self._last_error = "pymodbus not installed"
            return
        await self._ensure_connected()

    async def _on_stop(self) -> None:
        if self._client is not None:
            try:
                self._client.close()  # type: ignore
            except Exception:
                pass
            self._client = None
        self._connected = False

    async def _ensure_connected(self) -> None:
        if self._connected and self._client is not None:
            try:
                if self._client.connected:  # type: ignore
                    return
            except Exception:
                pass
        if not _HAS_PYMODBUS:
            return
        host = self.config.params.get("host", "127.0.0.1")
        port = int(self.config.params.get("port", 502))
        timeout = float(self.config.params.get("timeout_s", 3.0))
        self._client = AsyncModbusTcpClient(host=host, port=port, timeout=timeout)  # type: ignore
        try:
            await self._client.connect()  # type: ignore
            # pymodbus 3.x connect returns bool
            self._connected = bool(getattr(self._client, "connected", True))
            if not self._connected:
                # some versions return None on success; treat as connected if no exception
                self._connected = True
            self._status = "ok"
            self._last_error = None
        except Exception as e:
            self._last_error = f"Modbus connect {host}:{port} failed: {e}"
            self._connected = False
            self._status = "degraded"

    def _parse_tag(self, tag: str) -> tuple[int, int, int]:
        """Return (fc, address, count)."""
        parts = tag.split(":")
        if len(parts) < 2:
            raise ValueError(f"Invalid modbus tag {tag!r} — expected fc:address[:count]")
        fc = int(parts[0])
        addr = int(parts[1])
        count = int(parts[2]) if len(parts) > 2 else 1
        # infer count for float types if not specified handled by caller (use mapping.data_type)
        return fc, addr, count

    async def _read_tag_raw(self, tag: str, data_type: str) -> Optional[float]:
        if not _HAS_PYMODBUS or self._client is None:
            return None
        fc, addr, count = self._parse_tag(tag)
        # auto-expand count for 32-bit types
        if data_type.lower() in ("float32", "int32", "uint32") and count == 1:
            count = 2
        unit = int(self.config.params.get("unit_id", 1))
        try:
            if fc == 1:
                resp = await self._client.read_coils(addr, count=count, slave=unit)  # type: ignore
                if resp.isError():  # type: ignore
                    raise RuntimeError(f"Modbus coil read error: {resp}")
                # coils are bits
                return 1.0 if resp.bits and resp.bits[0] else 0.0  # type: ignore
            elif fc == 2:
                resp = await self._client.read_discrete_inputs(addr, count=count, slave=unit)  # type: ignore
                if resp.isError():  # type: ignore
                    raise RuntimeError(f"Discrete input error: {resp}")
                return 1.0 if resp.bits and resp.bits[0] else 0.0  # type: ignore
            elif fc == 3:
                resp = await self._client.read_holding_registers(addr, count=count, slave=unit)  # type: ignore
                if resp.isError():  # type: ignore
                    raise RuntimeError(f"Holding register read error: {resp}")
                regs = list(resp.registers)  # type: ignore
                return _decode_registers(regs, data_type)
            elif fc == 4:
                resp = await self._client.read_input_registers(addr, count=count, slave=unit)  # type: ignore
                if resp.isError():  # type: ignore
                    raise RuntimeError(f"Input register read error: {resp}")
                regs = list(resp.registers)  # type: ignore
                return _decode_registers(regs, data_type)
            else:
                raise ValueError(f"Unsupported function code {fc}")
        except Exception as e:
            self._last_error = f"modbus read {tag}: {e}"
            # mark disconnected so next poll reconnects
            self._connected = False
            return None

    async def _poll_once_impl(self) -> List[NormalizedReading]:
        # synthetic fallback if no real modbus
        if not _HAS_PYMODBUS or not self._connected:
            # try connect once; if still not connected, synthetic
            if _HAS_PYMODBUS and not self._connected:
                await self._ensure_connected()
                if not self._connected:
                    return self._synthetic_readings("not connected — synthetic fallback")
            elif not _HAS_PYMODBUS:
                return self._synthetic_readings("pymodbus not installed — synthetic fallback")

        readings: List[NormalizedReading] = []
        raw_cache: Dict[str, float] = {}

        # single tags
        for tm in self.config.tags:
            if tm.source_tags:
                continue
            raw = await self._read_tag_raw(tm.source_tag, tm.data_type)
            if raw is None:
                continue
            fval = normalize_raw_value(raw, tm)
            raw_cache[tm.source_tag] = fval
            value = apply_tag_mapping(fval, tm)
            readings.append(
                self._reading(
                    metric=tm.metric,
                    value=value,
                    unit=tm.unit,
                    source_tag=tm.source_tag,
                    quality=Quality.GOOD,
                    raw_value=fval,
                )
            )

        # compound
        for tm in self.config.tags:
            if not tm.source_tags:
                continue
            raw_by_var: Dict[str, float] = {}
            ok = True
            for var, tag in tm.source_tags.items():
                if tag in raw_cache:
                    raw_by_var[var] = raw_cache[tag]
                else:
                    rv = await self._read_tag_raw(tag, tm.data_type)
                    if rv is None:
                        ok = False
                        break
                    fval = normalize_raw_value(rv, tm)
                    raw_by_var[var] = fval
                    raw_cache[tag] = fval
            if not ok:
                continue
            try:
                value = compound(raw_by_var, tm)
            except Exception:
                continue
            readings.append(
                self._reading(
                    metric=tm.metric,
                    value=value,
                    unit=tm.unit,
                    source_tag=",".join(tm.source_tags.values()),
                    quality=Quality.GOOD,
                )
            )

        return readings

    def _synthetic_readings(self, reason: str) -> List[NormalizedReading]:
        import math

        readings: List[NormalizedReading] = []
        t = time.time()
        for tm in self.config.tags:
            h = abs(hash(tm.source_tag)) % 1000
            # interpret address to produce plausible range
            raw = 10.0 + (h % 50) + 3 * math.sin(t / 7.0 + h * 0.01)
            # if float32 etc still synthetic float
            fval = normalize_raw_value(raw, tm)
            value = apply_tag_mapping(fval, tm)
            readings.append(
                NormalizedReading(
                    station_id=self.config.station_id,
                    metric=tm.metric,
                    value=value,
                    unit=tm.unit,
                    timestamp=time.time(),
                    quality=Quality.UNCERTAIN,
                    protocol=self.protocol,
                    adapter_id=self.adapter_id,
                    source_tag=tm.source_tag,
                    raw_value=fval,
                )
            )
        return readings
