"""Tests — gateway RBAC matrix edge cases."""

from gateway.domain.models import Principal, Resource
from gateway.domain.policies import evaluate


def test_rbac_default_deny():
    p = Principal(sub="u", plant_id="p1", role="operator")
    # Try delete admin — operator should not have it
    r = Resource(service="gateway", path="/api/v1/admin/delete", action="delete", method="DELETE")
    dec = evaluate(p, r)
    assert not dec.allow


def test_viewer_read_only():
    p = Principal(sub="v", plant_id="p1", role="viewer")
    assert evaluate(p, Resource("gateway", "/api/v1/events", "read", method="GET")).allow
    assert not evaluate(p, Resource("gateway", "/api/v1/ingest", "post", method="POST")).allow


def test_reasoning_requires_admin_or_system():
    for role in ["operator", "viewer", "maintenance"]:
        p = Principal(sub="u", plant_id="p1", role=role)
        r = Resource("gateway", "/api/v1/reasoning/correlate", "post", method="POST")
        dec = evaluate(p, r)
        # operator/maintenance/viewer should NOT have reasoning post by default
        assert not dec.allow, f"{role} should not allow reasoning"
    # plant_admin and system allow reasoning
    for role in ["plant_admin", "system"]:
        p = Principal(sub="u", plant_id="p1", role=role)
        r = Resource("gateway", "/api/v1/reasoning/correlate", "post", method="POST")
        assert evaluate(p, r).allow


def test_plant_id_case_sensitive():
    p = Principal(sub="u", plant_id="Plant-A", role="operator")
    r = Resource("gateway", "/api/v1/events", "read", plant_id="plant-a", method="GET")
    dec = evaluate(p, r)
    assert not dec.allow  # case sensitive mismatch → deny
