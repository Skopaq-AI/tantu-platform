"""MQTT adapter — real paho-mqtt.

- Manages paho.mqtt.client.Client lifecycle (connect, subscribe, message callback)
- Topic map → metric via TagMapping (source_tag = MQTT topic filter)
- Payload parsing: JSON dict with optional json_path (e.g. "value", "data.pressure", "payload.reading")
- QoS, keepalive, LWT, reconnect with backoff
- Normalization + tag-map compounding
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional

from ...domain.events import Quality, NormalizedReading
from ...domain.models import AdapterConfig
from ...domain.tag_map import normalize_raw_value, apply_tag_mapping, compound
from ..base import BaseAdapter

try:
    import paho.mqtt.client as mqtt  # type: ignore

    _HAS_PAHO = True
except Exception:  # pragma: no cover
    _HAS_PAHO = False
    mqtt = None  # type: ignore


def _extract_json_path(payload: Any, path: Optional[str]) -> Any:
    """Extract value via dotted path. If path is None/empty returns payload itself (or payload['value'] heuristic)."""
    if path is None or path == "":
        if isinstance(payload, dict):
            # heuristic: common keys
            for k in ("value", "val", "reading", "data", "payload"):
                if k in payload:
                    v = payload[k]
                    if isinstance(v, (int, float)):
                        return v
                    if isinstance(v, dict) and "value" in v:
                        return v["value"]
            # if single numeric value in dict
            nums = [v for v in payload.values() if isinstance(v, (int, float))]
            if len(nums) == 1:
                return nums[0]
        return payload
    cur: Any = payload
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except Exception:
                return None
        else:
            return None
    return cur


class MqttAdapter(BaseAdapter):
    """MQTT adapter.

    config.params:
      host: broker host (default localhost)
      port: int (1883)
      client_id: str
      username / password: optional
      keepalive: int (60)
      qos: int (1)
      json_path: optional dotted path to value inside JSON payload (per-tag override via tag Mapping scale etc.)
      topics: optional list[str] — if not set, uses each TagMapping.source_tag as topic filter
      use_tls: bool
    """

    def __init__(self, config: AdapterConfig) -> None:
        super().__init__(config)
        self._client: Optional[Any] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._buffer: asyncio.Queue[NormalizedReading] = asyncio.Queue(maxsize=10000)
        self._topic_to_mappings: Dict[str, List[Any]] = {}

    async def _on_start(self) -> None:
        self._loop = asyncio.get_running_loop()
        # Build topic→mapping index
        self._topic_to_mappings.clear()
        for tm in self.config.tags:
            # support compound: index each source tag
            if tm.source_tags:
                for var, topic in tm.source_tags.items():
                    self._topic_to_mappings.setdefault(topic, []).append(tm)
            else:
                self._topic_to_mappings.setdefault(tm.source_tag, []).append(tm)

        if not _HAS_PAHO:
            self._status = "degraded"
            self._last_error = "paho-mqtt not installed — buffer-only mode"
            return

        host = self.config.params.get("host", "localhost")
        port = int(self.config.params.get("port", 1883))
        client_id = self.config.params.get("client_id", f"adapter-fabric-{self.adapter_id}")
        keepalive = int(self.config.params.get("keepalive", 60))
        qos = int(self.config.params.get("qos", 1))
        username = self.config.params.get("username")
        password = self.config.params.get("password")

        try:
            # paho-mqtt 2.x requires callback_api_version
            try:
                self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)  # type: ignore
            except Exception:
                self._client = mqtt.Client(client_id=client_id)  # type: ignore

            if username:
                self._client.username_pw_set(username, password)  # type: ignore

            if self.config.params.get("use_tls"):
                self._client.tls_set()  # type: ignore

            self._client.on_connect = self._on_connect  # type: ignore
            self._client.on_message = self._on_message  # type: ignore
            self._client.on_disconnect = self._on_disconnect  # type: ignore
            # LWT
            try:
                self._client.will_set(f"tantu/adapter/{self.adapter_id}/status", payload="offline", qos=1, retain=True)  # type: ignore
            except Exception:
                pass

            # connect async via loop_start (threaded network loop)
            self._client.connect_async(host, port, keepalive=keepalive)  # type: ignore
            self._client.loop_start()  # type: ignore
            self._status = "ok"
            self._last_ok_ts = time.time()
            # wait briefly for connect
            await asyncio.sleep(0.5)
        except Exception as e:
            self._last_error = f"MQTT connect {host}:{port} failed: {e}"
            self._status = "degraded"

    async def _on_stop(self) -> None:
        if self._client is not None:
            try:
                self._client.loop_stop()  # type: ignore
                self._client.disconnect()  # type: ignore
            except Exception:
                pass
            self._client = None

    # paho callbacks (run in paho network thread)
    def _on_connect(self, client, userdata, flags, reason_code, properties=None):  # type: ignore
        # paho v2: reason_code is int or ReasonCode
        rc = int(getattr(reason_code, "value", reason_code)) if reason_code is not None else 0
        if rc != 0:
            self._last_error = f"MQTT connect failed rc={rc}"
            self._status = "degraded"
            return
        self._status = "ok"
        self._last_ok_ts = time.time()
        qos = int(self.config.params.get("qos", 1))
        # explicit topics param overrides tag-derived topics
        topics = self.config.params.get("topics")
        if topics:
            for t in topics:
                try:
                    client.subscribe(t, qos=qos)  # type: ignore
                except Exception:
                    pass
        else:
            for topic in self._topic_to_mappings:
                try:
                    client.subscribe(topic, qos=qos)  # type: ignore
                except Exception:
                    pass

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):  # type: ignore
        self._status = "degraded"
        self._last_error = f"MQTT disconnected rc={reason_code}"

    def _on_message(self, client, userdata, msg):  # type: ignore
        topic = msg.topic
        payload_raw = msg.payload
        # schedule processing on event loop
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self._handle_message(topic, payload_raw))
            )
        else:
            # fallback sync
            try:
                asyncio.get_event_loop().call_soon_threadsafe(
                    lambda: asyncio.create_task(self._handle_message(topic, payload_raw))
                )
            except Exception:
                pass

    async def _handle_message(self, topic: str, payload_raw: bytes) -> None:
        # try JSON parse, else raw float
        try:
            text = payload_raw.decode("utf-8", errors="replace")
        except Exception:
            text = ""
        data: Any
        try:
            data = json.loads(text)
        except Exception:
            # try raw float
            try:
                data = float(text.strip())
            except Exception:
                data = text

        # match topic to mappings (exact + wildcard heuristic)
        matched: List[Any] = []
        if topic in self._topic_to_mappings:
            matched.extend(self._topic_to_mappings[topic])
        else:
            # wildcard support: "#" or "+" style — simple prefix match
            for pattern, mappings in self._topic_to_mappings.items():
                if self._topic_matches(pattern, topic):
                    matched.extend(mappings)

        for tm in matched:
            try:
                await self._process_mapping_for_topic(tm, topic, data)
            except Exception as e:
                self._error_count += 1
                self._last_error = f"mqtt process {topic}: {e}"

    def _topic_matches(self, pattern: str, topic: str) -> bool:
        # MQTT wildcard: + = single level, # = multi level suffix
        if pattern == topic:
            return True
        if "#" in pattern:
            prefix = pattern.split("#")[0].rstrip("/")
            return topic.startswith(prefix)
        if "+" in pattern:
            import fnmatch

            # translate + to * per level
            pat = pattern.replace("+", "*")
            return fnmatch.fnmatch(topic, pat)
        return False

    async def _process_mapping_for_topic(self, tm, topic: str, data: Any) -> None:
        # For compound mappings we need to buffer per-var values
        if tm.source_tags:
            # compound: data is payload for one var — store in per-adapter cache
            # Use in-memory dict keyed by metric
            var_for_topic = None
            for var, t in tm.source_tags.items():
                if t == topic or self._topic_matches(t, topic):
                    var_for_topic = var
                    break
            if var_for_topic is None:
                var_for_topic = next(iter(tm.source_tags))
            # extract numeric
            json_path = self.config.params.get("json_path") or tm.params.get("json_path") if hasattr(tm, "params") else None  # type: ignore
            # TagMapping has no params; use config json_path
            raw_val = _extract_json_path(data, json_path) if isinstance(data, dict) else data
            try:
                fval = normalize_raw_value(float(raw_val), tm)  # type: ignore
            except Exception:
                return
            # store in queue-adjacent dict _compound_cache
            if not hasattr(self, "_compound_cache"):
                self._compound_cache: Dict[str, Dict[str, float]] = {}  # type: ignore
            bucket = self._compound_cache.setdefault(tm.metric, {})
            bucket[var_for_topic] = fval
            # if we have all vars, emit compound
            if len(bucket) >= len(tm.source_tags):
                try:
                    value = compound(dict(bucket), tm)
                except Exception:
                    return
                reading = self._reading(metric=tm.metric, value=value, unit=tm.unit, source_tag=topic, raw_value=None)
                reading = NormalizedReading(
                    station_id=reading.station_id,
                    metric=reading.metric,
                    value=reading.value,
                    unit=reading.unit,
                    timestamp=reading.timestamp,
                    quality=Quality.GOOD,
                    protocol=self.protocol,
                    adapter_id=self.adapter_id,
                    source_tag=",".join(tm.source_tags.values()),
                )
                await self._enqueue(reading)
                bucket.clear()
            return

        # single tag
        json_path = self.config.params.get("json_path")
        raw_val: Any
        if isinstance(data, dict):
            raw_val = _extract_json_path(data, json_path)
        else:
            raw_val = data
        # if raw_val is dict still, try heuristic
        if isinstance(raw_val, dict):
            raw_val = _extract_json_path(raw_val, None)
        try:
            fval = normalize_raw_value(float(raw_val), tm)  # type: ignore
        except Exception:
            # if payload is already numeric string
            try:
                fval = normalize_raw_value(float(str(raw_val).strip()), tm)  # type: ignore
            except Exception:
                return
        value = apply_tag_mapping(fval, tm)
        reading = self._reading(metric=tm.metric, value=value, unit=tm.unit, source_tag=topic, raw_value=fval)
        await self._enqueue(reading)

    async def _enqueue(self, reading: NormalizedReading) -> None:
        self._message_count += 1
        self._last_ok_ts = time.time()
        self._status = "ok"
        try:
            self._queue.put_nowait(reading)
        except asyncio.QueueFull:
            try:
                self._queue.get_nowait()
            except Exception:
                pass
            self._queue.put_nowait(reading)
        # also metrics
        try:
            from ...infra import metrics as m

            m.READINGS_TOTAL.labels(protocol=self.protocol, adapter_id=self.adapter_id, metric=reading.metric).inc()
            m.ADAPTER_UP.labels(protocol=self.protocol, adapter_id=self.adapter_id).set(1)
        except Exception:
            pass

    # --- polling path (for tests / synthetic) ---
    async def _poll_once_impl(self) -> List[NormalizedReading]:
        # drain queue items that arrived via callback; if none, return empty (real MQTT is push)
        readings: List[NormalizedReading] = []
        while True:
            try:
                readings.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        # if synthetic mode (no broker) and no readings, optionally return synthetic for tags with no traffic
        if not readings and not _HAS_PAHO:
            return self._synthetic_readings()
        return readings

    def _synthetic_readings(self) -> List[NormalizedReading]:
        import math

        readings: List[NormalizedReading] = []
        t = time.time()
        for tm in self.config.tags:
            if tm.source_tags:
                continue
            h = abs(hash(tm.source_tag)) % 1000
            raw = 15.0 + (h % 40) + 2 * math.sin(t / 5.0)
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

    # test helper: inject message without broker
    async def inject_message(self, topic: str, payload: Any) -> None:
        if isinstance(payload, (dict, list)):
            raw = json.dumps(payload).encode()
        elif isinstance(payload, bytes):
            raw = payload
        else:
            raw = str(payload).encode()
        await self._handle_message(topic, raw)
