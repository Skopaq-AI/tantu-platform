"""Tests — OPA-style RBAC + ABAC plant scoping."""
import pytest

from gateway.domain.models import Principal, Resource
from gateway.domain.policies import evaluate


def _p(role="operator", plant_id="plant-a", extra=None):
    return Principal(sub="u1", plant_id=plant_id, role=role, extra=extra or {})


def _r(path="/api/v1/events", method="GET", plant_id=None, service="gateway", action="*"):
    return Resource(service=service, path=path, action=action, plant_id=plant_id, method=method)


def test_operator_can_read_events_same_plant_via_header_scoping():
    principal = _p("operator", "plant-a")
    resource = _r("/api/v1/events", "GET", plant_id=None)  # no explicit plant → RBAC allow
    dec = evaluate(principal, resource)
    assert dec.allow, dec.reason

def test_operator_denied_for_plant_mismatch_abac():
    principal = _p("operator", "plant-a")
    resource = _r("/api/v1/events", "GET", plant_id="plant-b")
    dec = evaluate(principal, resource)
    assert not dec.allow
    assert "ABAC" in dec.reason

def test_plant_admin_wildcard_within_plant():
    principal = _p("plant_admin", "plant-a")
    for path in ["/api/v1/ingest", "/api/v1/events", "/api/v1/reasoning/ask", "/health"]:
        dec = evaluate(principal, _r(path, "POST" if "ingest" in path else "GET"))
        assert dec.allow, f"plant_admin should allow {path}: {dec.reason}"

def test_plant_admin_cannot_cross_plant():
    principal = _p("plant_admin", "plant-a")
    dec = evaluate(principal, _r("/api/v1/events", "GET", plant_id="plant-b"))
    assert not dec.allow

def test_viewer_cannot_ingest():
    principal = _p("viewer", "plant-a")
    dec = evaluate(principal, _r("/api/v1/ingest", "POST"))
    assert not dec.allow
    assert "RBAC" in dec.reason

def test_operator_can_ingest_same_plant():
    principal = _p("operator", "plant-a")
    dec = evaluate(principal, _r("/api/v1/ingest", "POST"))
    assert dec.allow

def test_maintenance_can_write_maintenance():
    principal = _p("maintenance", "plant-a")
    dec = evaluate(principal, _r("/api/v1/maintenance/action", "POST"))
    assert dec.allow

def test_operator_cannot_write_maintenance():
    principal = _p("operator", "plant-a")
    dec = evaluate(principal, _r("/api/v1/maintenance/action", "POST"))
    assert not dec.allow

def test_unknown_role_denied():
    principal = _p("unknown_role", "plant-a")
    dec = evaluate(principal, _r("/api/v1/events", "GET"))
    assert not dec.allow

def test_system_cross_plant_wildcard():
    principal = _p("system", "plant-a", extra={"plant_ids": ["*"]})
    dec = evaluate(principal, _r("/api/v1/events", "GET", plant_id="plant-b"))
    assert dec.allow

def test_system_without_wildcard_still_blocked_cross_plant():
    principal = _p("system", "plant-a")
    dec = evaluate(principal, _r("/api/v1/events", "GET", plant_id="plant-b"))
    assert not dec.allow

def test_health_allowed_for_all_roles():
    for role in ["operator", "viewer", "maintenance", "plant_admin", "system"]:
        dec = evaluate(_p(role, "plant-a"), _r("/health", "GET"))
        assert dec.allow, f"{role} should access /health"

def test_abac_allows_when_no_plant_scope():
    # Resource with no plant_id → ABAC not applied
    principal = _p("operator", "plant-a")
    dec = evaluate(principal, _r("/api/v1/reasoning/ask", "POST", plant_id=None))
    # reasoning is not in operator perms — should deny via RBAC
    # but if reasoning path, operator has no reasoning perm, so deny is expected
    assert not dec.allow
    # plant_admin with no plant scope should allow
    dec2 = evaluate(_p("plant_admin", "plant-a"), _r("/api/v1/reasoning/ask", "POST", plant_id=None))
    assert dec2.allow
