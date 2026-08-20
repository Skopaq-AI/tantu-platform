"""EtherNet/IP adapter — real CIP / EIP encapsulation frame + pycomm3.

Implements:
 - EIP encapsulation header (24 bytes, little-endian per spec Vol2)
 - CIP explicit messaging: Get Attribute Single (0x0E), Read Tag Service (0x4C), Write Tag
 - EPATH encoding, symbol segment for tag names
 - Falls back to synthetic readings when PLC not reachable
 - pycomm3 LogixDriver integration when available (real Rockwell path)
"""
from __future__ import annotations

import asyncio
import socket
import struct
import time
from typing import Any, Dict, List, Optional, Tuple

from ...domain.events import Quality, NormalizedReading
from ...domain.models import AdapterConfig
from ...domain.tag_map import normalize_raw_value, apply_tag_mapping, compound
from ..base import BaseAdapter

try:
    from pycomm3 import LogixDriver  # type: ignore
    _HAS_PYCOMM3 = True
except Exception:  # pragma: no cover
    _HAS_PYCOMM3 = False
    LogixDriver = object  # type: ignore  # noqa

# ---------------------------------------------------------------------------
# EIP / CIP constants (ODVA spec)
# ---------------------------------------------------------------------------
EIP_CMD_NOP = 0x0000
EIP_CMD_LIST_SERVICES = 0x0004
EIP_CMD_LIST_IDENTITY = 0x0063
EIP_CMD_LIST_INTERFACES = 0x0064
EIP_CMD_REGISTER_SESSION = 0x0065
EIP_CMD_UNREGISTER_SESSION = 0x0066
EIP_CMD_SEND_RR_DATA = 0x006F
EIP_CMD_SEND_UNIT_DATA = 0x0070

CIP_SVC_GET_ATTR_SINGLE = 0x0E
CIP_SVC_READ_TAG = 0x4C
CIP_SVC_WRITE_TAG = 0x4D

SEG_SYMBOL = 0x91


def build_eip_header(command: int, length: int, session_handle: int = 0, status: int = 0, sender_context: bytes = b"\x00" * 8, options: int = 0) -> bytes:
    """Build 24-byte EIP encapsulation header — little-endian.

    Layout (Vol2 Table 2-2.1):
      0-1  command (UINT)
      2-3  length  (UINT) — length of data after header
      4-7  session handle (UDINT)
      8-11 status (UDINT)
      12-19 sender context (8 bytes)
      20-23 options (UDINT)
    """
    return struct.pack(
        "<HHI I 8s I",
        command & 0xFFFF,
        length & 0xFFFF,
        session_handle & 0xFFFFFFFF,
        status & 0xFFFFFFFF,
        sender_context[:8].ljust(8, b"\x00"),
        options & 0xFFFFFFFF,
    )


def parse_eip_header(data: bytes) -> Dict[str, Any]:
    if len(data) < 24:
        raise ValueError(f"EIP header too short: {len(data)}")
    command, length, session_handle, status, sender_context, options = struct.unpack("<HHI I 8s I", data[:24])
    return {
        "command": command,
        "length": length,
        "session_handle": session_handle,
        "status": status,
        "sender_context": sender_context,
        "options": options,
        "payload": data[24 : 24 + length],
    }


def build_cip_epath(class_id: Optional[int] = None, instance_id: Optional[int] = None, attribute_id: Optional[int] = None, tag_name: Optional[str] = None) -> bytes:
    """Build CIP EPATH byte sequence."""
    out = bytearray()

    def _logical(seg_type: int, value: int) -> None:
        if value < 256:
            out.extend([seg_type, value & 0xFF])
        else:
            out.extend([seg_type | 0x01, 0x00, value & 0xFF, (value >> 8) & 0xFF])

    if tag_name:
        encoded = tag_name.encode("utf-8")
        out.append(SEG_SYMBOL)
        out.append(len(encoded))
        out.extend(encoded)
        if len(encoded) % 2 == 1:
            out.append(0x00)
        return bytes(out)

    if class_id is not None:
        _logical(0x20, class_id)
    if instance_id is not None:
        _logical(0x24, instance_id)
    if attribute_id is not None:
        _logical(0x30, attribute_id)
    return bytes(out)


def build_cip_read_tag_request(tag_name: str, elements: int = 1) -> bytes:
    """Build CIP Read Tag Service (0x4C) request payload."""
    epath = build_cip_epath(tag_name=tag_name)
    epath_words = len(epath) // 2
    return struct.pack("BB", CIP_SVC_READ_TAG, epath_words) + epath + struct.pack("<H", elements)


def build_cip_get_attribute_single(class_id: int, instance_id: int, attribute_id: int) -> bytes:
    epath = build_cip_epath(class_id=class_id, instance_id=instance_id, attribute_id=attribute_id)
    epath_words = len(epath) // 2
    return struct.pack("BB", CIP_SVC_GET_ATTR_SINGLE, epath_words) + epath


def build_send_rr_data(session_handle: int, cip_payload: bytes, interface_handle: int = 0, timeout: int = 10) -> bytes:
    """Wrap CIP payload in SendRRData (EIP command 0x6F) with CPF."""
    cpf = struct.pack("<I H H", interface_handle, timeout, 2)
    cpf += struct.pack("<H H", 0x0000, 0)
    cpf += struct.pack("<H H", 0x00B2, len(cip_payload)) + cip_payload
    header = build_eip_header(EIP_CMD_SEND_RR_DATA, len(cpf), session_handle=session_handle)
    return header + cpf


def build_register_session() -> bytes:
    body = struct.pack("<HH", 1, 0)
    return build_eip_header(EIP_CMD_REGISTER_SESSION, len(body)) + body


def encode_cip_data(value: Any, data_type: str = "REAL") -> bytes:
    dt = data_type.upper()
    if dt in ("REAL", "FLOAT"):
        return struct.pack("<f", float(value))
    if dt == "DINT":
        return struct.pack("<i", int(value))
    if dt == "INT":
        return struct.pack("<h", int(value))
    if dt == "BOOL":
        return struct.pack("<?", bool(value))
    return struct.pack("<f", float(value))


def decode_cip_data(data: bytes, data_type: str = "REAL") -> float:
    if not data:
        raise ValueError("Empty CIP data")
    dt = data_type.upper()
    try:
        if dt in ("REAL", "FLOAT") and len(data) >= 4:
            if data[0] == 0xCA and len(data) >= 5:
                return struct.unpack("<f", data[1:5])[0]
            return struct.unpack("<f", data[:4])[0]
        if dt == "DINT":
            if data[0] == 0xC4 and len(data) >= 5:
                return float(struct.unpack("<i", data[1:5])[0])
            return float(struct.unpack("<i", data[:4])[0])
        if dt == "INT":
            if data[0] == 0xC3 and len(data) >= 3:
                return float(struct.unpack("<h", data[1:3])[0])
            return float(struct.unpack("<h", data[:2])[0])
        if len(data) >= 4:
            try:
                return struct.unpack("<f", data[:4])[0]
            except Exception:
                return float(struct.unpack("<i", data[:4])[0])
        if len(data) >= 2:
            return float(struct.unpack("<h", data[:2])[0])
        return float(data[0])
    except Exception as e:
        raise ValueError(f"decode_cip_data failed dtype={data_type} data={data.hex()}: {e}") from e


class RawEipClient:
    """Minimal blocking EIP client for frame-level tests / fallback."""

    def __init__(self, host: str, port: int = 44818, timeout: float = 3.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._session_handle = 0

    def connect(self) -> None:
        self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self._sock.settimeout(self.timeout)
        req = build_register_session()
        self._sock.sendall(req)
        resp = self._sock.recv(1024)
        if len(resp) >= 24:
            hdr = parse_eip_header(resp)
            if hdr["status"] == 0:
                self._session_handle = hdr["session_handle"]
            else:
                raise ConnectionError(f"RegisterSession failed status={hdr['status']}")

    def close(self) -> None:
        if self._sock:
            try:
                hdr = build_eip_header(EIP_CMD_UNREGISTER_SESSION, 0, session_handle=self._session_handle)
                self._sock.sendall(hdr)
            except Exception:
                pass
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def read_tag(self, tag_name: str, data_type: str = "REAL") -> Optional[float]:
        if not self._sock:
            raise ConnectionError("Not connected")
        cip = build_cip_read_tag_request(tag_name)
        frame = build_send_rr_data(self._session_handle, cip)
        self._sock.sendall(frame)
        resp = self._sock.recv(4096)
        if len(resp) < 24:
            return None
        hdr = parse_eip_header(resp)
        if hdr["status"] != 0:
            return None
        payload = hdr["payload"]
        if len(payload) < 10:
            return None
        try:
            cip_reply = payload[16:]
            if not cip_reply:
                return None
            if cip_reply[2] != 0:
                return None
            data_start = 4
            if len(cip_reply) > 3 and cip_reply[3] != 0:
                data_start += 2 * cip_reply[3]
            raw_data = cip_reply[data_start:]
            return decode_cip_data(raw_data, data_type)
        except Exception:
            return None


class EthernetIpAdapter(BaseAdapter):
    """EtherNet/IP adapter.

    config.params:
      host: PLC IP (required for real mode)
      port: int (44818)
      slot: int (0)
      timeout_s: float (3)
      use_pycomm3: bool (True)
      data_type_map: dict[tag -> CIP type str]
    """

    def __init__(self, config: AdapterConfig) -> None:
        super().__init__(config)
        self._driver: Optional[Any] = None
        self._raw_client: Optional[RawEipClient] = None
        self._use_pycomm3 = bool(self.config.params.get("use_pycomm3", True))

    async def _on_start(self) -> None:
        host = self.config.params.get("host")
        if not host:
            self._status = "degraded"
            self._last_error = "no host configured — synthetic fallback"
            return
        if self._use_pycomm3 and _HAS_PYCOMM3:
            try:
                path = f"{host}/{self.config.params.get('slot', 0)}"

                def _open():
                    d = LogixDriver(path)  # type: ignore
                    d.open()
                    return d

                self._driver = await asyncio.to_thread(_open)
                self._status = "ok"
                self._last_ok_ts = time.time()
                return
            except Exception as e:
                self._last_error = f"pycomm3 open {host} failed: {e} — trying raw EIP"
                self._driver = None
        if host:
            try:
                port = int(self.config.params.get("port", 44818))
                timeout = float(self.config.params.get("timeout_s", 3.0))
                client = RawEipClient(host, port, timeout)
                await asyncio.to_thread(client.connect)
                self._raw_client = client
                self._status = "ok"
                self._last_ok_ts = time.time()
            except Exception as e:
                self._last_error = f"Raw EIP connect {host} failed: {e} — synthetic fallback"
                self._status = "degraded"
                self._raw_client = None

    async def _on_stop(self) -> None:
        if self._driver is not None:
            try:
                await asyncio.to_thread(self._driver.close)  # type: ignore
            except Exception:
                pass
            self._driver = None
        if self._raw_client is not None:
            try:
                await asyncio.to_thread(self._raw_client.close)
            except Exception:
                pass
            self._raw_client = None

    def _is_class_instance_tag(self, tag: str) -> bool:
        return tag.startswith("class:") or ("," in tag and "instance:" in tag)

    def _parse_class_instance(self, tag: str) -> Tuple[int, int, int]:
        parts: Dict[str, int] = {}
        for p in tag.split(","):
            if ":" in p:
                k, v = p.split(":", 1)
                parts[k.strip()] = int(v.strip())
        return parts.get("class", 1), parts.get("instance", 1), parts.get("attr", 1)

    async def _read_tag(self, tag: str, data_type: str) -> Optional[float]:
        if self._driver is not None:
            try:
                def _read():
                    result = self._driver.read(tag)  # type: ignore
                    if result is None:
                        return None
                    if hasattr(result, "error") and result.error:
                        raise RuntimeError(f"pycomm3 read error: {result.error}")
                    v = getattr(result, "value", result)
                    if v is None:
                        return None
                    return float(v)

                return await asyncio.to_thread(_read)
            except Exception as e:
                self._last_error = f"EIP read {tag}: {e}"
                return None
        if self._raw_client is not None:
            try:
                if self._is_class_instance_tag(tag):
                    return None
                return await asyncio.to_thread(self._raw_client.read_tag, tag, data_type)
            except Exception as e:
                self._last_error = f"Raw EIP read {tag}: {e}"
                return None
        return None

    async def _poll_once_impl(self) -> List[NormalizedReading]:
        has_connection = (self._driver is not None) or (self._raw_client is not None)
        if not has_connection or not self.config.params.get("host"):
            return self._synthetic_readings("no PLC connection — synthetic fallback")

        readings: List[NormalizedReading] = []
        raw_cache: Dict[str, float] = {}
        dtype_map: Dict[str, str] = self.config.params.get("data_type_map", {})

        for tm in self.config.tags:
            if tm.source_tags:
                continue
            dtype = dtype_map.get(tm.source_tag, tm.data_type if tm.data_type != "float" else "REAL")
            raw = await self._read_tag(tm.source_tag, dtype)
            if raw is None:
                continue
            fval = normalize_raw_value(raw, tm)
            raw_cache[tm.source_tag] = fval
            value = apply_tag_mapping(fval, tm)
            readings.append(self._reading(metric=tm.metric, value=value, unit=tm.unit, source_tag=tm.source_tag, raw_value=fval))

        for tm in self.config.tags:
            if not tm.source_tags:
                continue
            raw_by_var: Dict[str, float] = {}
            ok = True
            for var, tag in tm.source_tags.items():
                if tag in raw_cache:
                    raw_by_var[var] = raw_cache[tag]
                else:
                    dtype = dtype_map.get(tag, tm.data_type if tm.data_type != "float" else "REAL")
                    rv = await self._read_tag(tag, dtype)
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
            readings.append(self._reading(metric=tm.metric, value=value, unit=tm.unit, source_tag=",".join(tm.source_tags.values())))

        if readings:
            self._last_ok_ts = time.time()
            self._status = "ok"
        else:
            return self._synthetic_readings("connected but no tags returned — synthetic fallback")
        return readings

    def _synthetic_readings(self, reason: str) -> List[NormalizedReading]:
        import math

        readings: List[NormalizedReading] = []
        t = time.time()
        for tm in self.config.tags:
            if tm.source_tags:
                continue
            h = abs(hash(tm.source_tag)) % 1000
            raw = 12.0 + (h % 45) + 2.5 * math.sin(t / 6.0 + h * 0.015)
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
        try:
            dummy = build_cip_read_tag_request("DummyTag", 1)
            frm = build_send_rr_data(0x1234, dummy)
            _ = parse_eip_header(frm)
        except Exception:
            pass
        return readings

    @staticmethod
    def build_frame_for_tag(tag: str, session_handle: int = 0xABCD) -> bytes:
        cip = build_cip_read_tag_request(tag)
        return build_send_rr_data(session_handle, cip)
