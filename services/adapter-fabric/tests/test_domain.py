"""Domain tests — tag_map, events, models."""
import pytest

from adapter_fabric.domain.events import DefectEvent, Track, DefectClass, NormalizedReading, Quality
from adapter_fabric.domain.models import TagMapping
from adapter_fabric.domain.tag_map import apply_tag_mapping, compound, normalize_raw_value, evaluate_compound_formula


def test_defect_event_has_no_image_field():
    import dataclasses

    fields = {f.name for f in dataclasses.fields(DefectEvent)}
    assert "image" not in fields
    assert "image_bytes" not in fields
    assert "frame" not in fields
    # ensure no field name contains image/frame substring
    for fname in fields:
        assert "image" not in fname.lower()
        assert "frame" not in fname.lower()
        assert "bytes" not in fname.lower() or fname in ("__slot__",)


def test_normalized_reading_schema():
    r = NormalizedReading(station_id="s1", metric="pressure_bar", value=5.1, unit="bar", protocol="opcua", adapter_id="opcua-1", source_tag="ns=2;i=1001")
    assert r.metric == "pressure_bar"
    assert r.quality == Quality.GOOD


def test_scale_offset():
    tm = TagMapping(source_tag="ns=2;i=1001", metric="pressure_bar", unit="bar", scale=0.1, offset=1.0)
    assert apply_tag_mapping(100, tm) == pytest.approx(11.0)
    assert apply_tag_mapping(0, tm) == pytest.approx(1.0)


def test_compound_formula():
    tm = TagMapping(source_tag="compound", metric="pressure_avg", unit="bar", compound_formula="(a + b) / 2", source_tags={"a": "ns=2;i=1", "b": "ns=2;i=2"})
    v = compound({"a": 10, "b": 20}, tm)
    assert v == pytest.approx(15.0)


def test_compound_maths():
    assert evaluate_compound_formula("sqrt(a*a + b*b)", {"a": 3, "b": 4}) == pytest.approx(5.0)
    assert evaluate_compound_formula("abs(a - b) * 2", {"a": 10, "b": 7}) == pytest.approx(6.0)
    # disallowed node should raise
    with pytest.raises(ValueError):
        evaluate_compound_formula("__import__('os').system('echo pwned')", {"a": 1})


def test_normalize_raw_uint16_wrap():
    tm = TagMapping(source_tag="3:100", metric="count", unit="", data_type="uint16")
    assert normalize_raw_value(-1, tm) == pytest.approx(65535.0)
    tm2 = TagMapping(source_tag="3:100", metric="temp", unit="C", data_type="int16")
    assert normalize_raw_value(65535, tm2) == pytest.approx(65535.0)  # no wrap for int16 input int


def test_normalize_bool():
    tm = TagMapping(source_tag="1:5", metric="relay", unit="", data_type="bool")
    assert normalize_raw_value(1, tm) == 1.0
    assert normalize_raw_value(0, tm) == 0.0
    assert normalize_raw_value(True, tm) == 1.0
