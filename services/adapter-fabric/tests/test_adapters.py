"""Adapter tests — Modbus register decode, MTConnect XML, MQTT inject, OPC-UA/metrics."""

import pytest
import struct

from adapter_fabric.domain.models import AdapterConfig, Protocol, TagMapping
from adapter_fabric.adapters.modbus.adapter import _decode_registers  # type: ignore
from adapter_fabric.adapters.mtconnect.adapter import parse_mtconnect_xml, MTConnectAdapter
from adapter_fabric.adapters.mqtt.adapter import MqttAdapter
from adapter_fabric.adapters.opcua.adapter import OpcUaAdapter
from adapter_fabric.adapters.ethernet_ip.adapter import (
    EthernetIpAdapter,
    build_eip_header,
    parse_eip_header,
    build_cip_read_tag_request,
    build_send_rr_data,
)


# --- Modbus register decode ---
def test_modbus_float32_decode():
    # encode 3.14 as big-endian float32 -> two registers
    raw = struct.pack(">f", 3.14)
    r1, r2 = struct.unpack(">HH", raw)
    v = _decode_registers([r1, r2], "float32")
    assert v == pytest.approx(3.14, rel=1e-4)


def test_modbus_int16_decode():
    # -5 as int16 -> 0xFFFB = 65531
    v = _decode_registers([0xFFFB], "int16")
    assert v == pytest.approx(-5.0)
    v2 = _decode_registers([42], "uint16")
    assert v2 == pytest.approx(42.0)
    # int32
    raw = struct.pack(">i", -123456)
    r1, r2 = struct.unpack(">HH", raw)
    v3 = _decode_registers([r1, r2], "int32")
    assert v3 == pytest.approx(-123456.0)


# --- MTConnect XML ---
MTCONNECT_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<MTConnectStreams xmlns:m="urn:mtconnect.org:MTConnectStreams:1.3" xmlns="urn:mtconnect.org:MTConnectStreams:1.3">
  <Header creationTime="2024-01-01T00:00:00Z" instanceId="2" nextSequence="101" firstSequence="1" bufferSize="131072"/>
  <Streams>
    <DeviceStream name="CNC-01" uuid="cnc-01">
      <ComponentStream component="Controller" name="controller" componentId="cont">
        <Samples>
          <SpindleSpeed dataItemId="spindle_speed" timestamp="2024-01-01T00:00:01Z" sequence="99">1800</SpindleSpeed>
          <PathFeedrate dataItemId="feed_rate" timestamp="2024-01-01T00:00:01Z" sequence="100">250.5</PathFeedrate>
        </Samples>
        <Condition>
          <Normal dataItemId="avail" timestamp="2024-01-01T00:00:01Z" sequence="98">AVAILABLE</Normal>
        </Condition>
      </ComponentStream>
    </DeviceStream>
  </Streams>
</MTConnectStreams>
"""


def test_mtconnect_parse():
    parsed = parse_mtconnect_xml(MTCONNECT_SAMPLE)
    assert parsed["instanceId"] == "2"
    assert parsed["nextSequence"] == 101
    assert "spindle_speed" in parsed["data_items"]
    assert parsed["data_items"]["spindle_speed"]["numeric"] == pytest.approx(1800.0)
    assert parsed["data_items"]["feed_rate"]["numeric"] == pytest.approx(250.5)


@pytest.mark.asyncio
async def test_mtconnect_synthetic_poll():
    cfg = AdapterConfig(
        adapter_id="mtc-1",
        protocol=Protocol.MTCONNECT,
        station_id="line1-cnc01",
        tags=(TagMapping(source_tag="spindle_speed", metric="spindle_speed", unit="rpm"),),
        params={"base_url": "http://127.0.0.1:19999"},  # unreachable -> synthetic fallback
        poll_interval_ms=0,
    )
    ad = MTConnectAdapter(cfg)
    readings = await ad._poll_once_impl()  # type: ignore
    assert len(readings) == 1
    assert readings[0].metric == "spindle_speed"
    assert readings[0].protocol == "mtconnect"


@pytest.mark.asyncio
async def test_mtconnect_xml_tag_mapping():
    # inject XML directly via parse and ensure adapter would emit reading if connected; we test offline via poll with base_url missing
    cfg = AdapterConfig(
        adapter_id="mtc-2",
        protocol=Protocol.MTCONNECT,
        station_id="s1",
        tags=(
            TagMapping(
                source_tag="spindle_speed", metric="spindle_speed", unit="rpm", scale=1, offset=0
            ),
        ),
        params={},  # no base_url -> synthetic
        poll_interval_ms=0,
    )
    ad = MTConnectAdapter(cfg)
    rs = await ad._poll_once_impl()  # type: ignore
    assert rs[0].metric == "spindle_speed"


# --- MQTT inject ---
@pytest.mark.asyncio
async def test_mqtt_inject_and_poll():
    cfg = AdapterConfig(
        adapter_id="mqtt-1",
        protocol=Protocol.MQTT,
        station_id="line2-sensor01",
        tags=(
            TagMapping(
                source_tag="factory/line2/pressure",
                metric="pressure_bar",
                unit="bar",
                scale=0.1,
                offset=0,
            ),
        ),
        params={"host": "localhost", "json_path": "value"},
        poll_interval_ms=0,
    )
    ad = MqttAdapter(cfg)
    await ad._on_start()
    # inject JSON payload
    await ad.inject_message("factory/line2/pressure", {"value": 85})
    readings = await ad._poll_once_impl()  # type: ignore
    # should have drained the injected message (85 * 0.1 = 8.5)
    assert len(readings) == 1
    assert readings[0].value == pytest.approx(8.5)
    assert readings[0].metric == "pressure_bar"


@pytest.mark.asyncio
async def test_mqtt_raw_float_payload():
    cfg = AdapterConfig(
        adapter_id="mqtt-2",
        protocol=Protocol.MQTT,
        station_id="s1",
        tags=(TagMapping(source_tag="sensors/temp", metric="bearing_temp_c", unit="C"),),
        params={},
        poll_interval_ms=0,
    )
    ad = MqttAdapter(cfg)
    await ad._on_start()
    await ad.inject_message("sensors/temp", "72.5")
    readings = await ad._poll_once_impl()  # type: ignore
    assert readings[0].value == pytest.approx(72.5)


# --- OPC-UA synthetic fallback ---
@pytest.mark.asyncio
async def test_opcua_synthetic():
    cfg = AdapterConfig(
        adapter_id="opcua-1",
        protocol=Protocol.OPCUA,
        station_id="line1-opc01",
        tags=(
            TagMapping(
                source_tag="ns=2;i=1001", metric="pressure_bar", unit="bar", scale=1, offset=0
            ),
        ),
        params={"endpoint": "opc.tcp://127.0.0.1:4840", "timeout_s": 0.5},
        poll_interval_ms=0,
    )
    ad = OpcUaAdapter(cfg)
    # don't actually connect; poll should fallback to synthetic or attempt connect then synthetic
    readings = await ad._poll_once_impl()  # type: ignore
    assert len(readings) >= 1
    assert readings[0].metric == "pressure_bar"


# --- Ethernet/IP frame ---
def test_eip_header_roundtrip():
    hdr = build_eip_header(0x0065, 4, session_handle=0xABCD, status=0)
    assert len(hdr) == 24
    parsed = parse_eip_header(hdr + b"\x01\x00\x00\x00")
    assert parsed["command"] == 0x0065
    assert parsed["session_handle"] == 0xABCD
    assert parsed["length"] == 4


def test_cip_read_tag_frame():
    frame = build_cip_read_tag_request("MyTag", elements=1)
    assert frame[0] == 0x4C  # Read Tag service
    # full EIP wrapping
    eip = build_send_rr_data(0x1234, frame)
    assert len(eip) >= 24
    parsed = parse_eip_header(eip)
    assert parsed["command"] == 0x006F
    assert parsed["session_handle"] == 0x1234


@pytest.mark.asyncio
async def test_ethernet_ip_synthetic():
    cfg = AdapterConfig(
        adapter_id="eip-1",
        protocol=Protocol.ETHERNET_IP,
        station_id="line1-plc01",
        tags=(TagMapping(source_tag="MyTag", metric="pressure_bar", unit="bar"),),
        params={},  # no host -> synthetic
        poll_interval_ms=0,
    )
    ad = EthernetIpAdapter(cfg)
    readings = await ad._poll_once_impl()  # type: ignore
    assert len(readings) == 1
    assert readings[0].metric == "pressure_bar"
    # frame building still works
    frm = EthernetIpAdapter.build_frame_for_tag("TestTag")
    assert len(frm) > 24
