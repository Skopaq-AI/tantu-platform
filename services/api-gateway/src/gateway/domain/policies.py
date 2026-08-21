"""OPA-style RBAC + ABAC — pure, testable, no I/O.

Policy structure mimics OPA Rego decisions:
  allow if { role_has_permission AND plant_in_scope }

No grants are implicit — default deny.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import Principal, Resource

# ── Role → allowed (action, resource) matrix ──────────────────────────
# Action vocabulary: read, write, post, delete, health, *
# Resource vocabulary: telemetry, events, ingest, maintenance, reports, reasoning, admin, health, *
# Tuple means (action, resource). Wildcard "*" matches any.
ROLE_PERMISSIONS: dict[str, set[tuple[str, str]]] = {
    "operator": {
        ("read", "telemetry"),
        ("read", "events"),
        ("read", "reports"),
        ("post", "ingest"),
        ("read", "health"),
        ("health", "health"),
    },
    "maintenance": {
        ("read", "telemetry"),
        ("read", "events"),
        ("read", "reports"),
        ("read", "health"),
        ("health", "health"),
        ("post", "ingest"),
        ("write", "maintenance"),
        ("post", "maintenance"),
        ("read", "maintenance"),
    },
    "plant_admin": {
        ("*", "*"),  # wildcard — all actions/resources within plant
    },
    "viewer": {
        ("read", "telemetry"),
        ("read", "events"),
        ("read", "reports"),
        ("read", "health"),
        ("health", "health"),
    },
    "system": {
        ("*", "*"),
        ("post", "ingest"),
        ("read", "telemetry"),
        ("read", "events"),
        ("read", "health"),
        ("health", "health"),
    },
}


# ── Resource mapping — maps (service, path, method) → (resource, action) ──
def _infer_resource_action(service: str, path: str, method: str) -> tuple[str, str]:
    """Heuristic inference for resource/action from REST shape."""
    p = path.lower()
    m = method.upper()
    # health is universal
    if p.endswith("/health") or p.endswith("/health/live") or p.endswith("/ready"):
        return ("health", "health")
    if p.endswith("/metrics"):
        return ("health", "health")
    # ingest
    if "ingest" in p:
        return ("ingest", "post" if m == "POST" else "write")
    # events
    if "events" in p:
        if m == "GET":
            return ("events", "read")
        return ("events", "write")
    # reports / correlation
    if "report" in p or "correlation" in p:
        if m == "GET":
            return ("reports", "read")
        return ("reports", "write")
    # telemetry
    if "telemetry" in p or "readings" in p:
        return ("telemetry", "read" if m == "GET" else "write")
    # maintenance
    if "maintenance" in p:
        return ("maintenance", "write" if m in ("POST", "PUT", "PATCH") else "read")
    # reasoning
    if "reasoning" in p or "ask" in p or "correlate" in p or "rag" in p:
        if m == "POST":
            return ("reasoning", "post")
        return ("reasoning", "read")
    # adapter
    if "adapter" in p:
        return ("telemetry", "read" if m == "GET" else "write")
    # default: infer from method
    if m == "GET":
        return ("telemetry", "read")
    if m in ("POST", "PUT", "PATCH"):
        return ("telemetry", "write")
    if m == "DELETE":
        return ("admin", "delete")
    return ("telemetry", "read")


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allow: bool
    reason: str
    matched_permission: Optional[tuple[str, str]] = None


def _role_allows(role: str, action: str, resource: str) -> tuple[bool, Optional[tuple[str, str]]]:
    perms = ROLE_PERMISSIONS.get(role)
    if perms is None:
        return False, None
    # exact match
    if (action, resource) in perms:
        return True, (action, resource)
    # wildcard checks
    for a, r in perms:
        if a == "*" and r == "*":
            return True, (a, r)
        if a == "*" and r == resource:
            return True, (a, r)
        if a == action and r == "*":
            return True, (a, r)
    # health special: ("*", "*") already handled; ("health","health") handled
    return False, None


def evaluate(principal: Principal, resource: Resource) -> PolicyDecision:
    """OPA-style decision: RBAC then ABAC plant scoping.

    1. RBAC: role must grant (action, resource).
    2. ABAC: if resource.plant_id is not None, it must equal principal.plant_id,
       unless principal has a wildcard plant scope (system role with extra.plant_ids = ["*"]).
    """
    # Normalize
    role = principal.role
    inferred_res, inferred_action = _infer_resource_action(
        resource.service, resource.path, resource.method
    )
    # Choose effective action/resource
    # - If caller passed explicit non-default action (not "", "read", "*"), respect it
    # - If caller passed "*", resolve to inferred action (treat "*" as "any — infer")
    # - Otherwise (default "read" or "*" ), use inferred
    if resource.action in ("", "*", "read"):
        eff_action = inferred_action
        eff_resource = inferred_res
    else:
        eff_action = resource.action
        eff_resource = inferred_res
        # If caller gave explicit action but inferred resource is more specific, keep inferred resource
        # (resource service is gateway, not helpful)

    # Special bypass: health endpoints are readable by any authenticated principal; unauth handled upstream.
    # Still enforce RBAC but health is in every role except unknown.
    allowed, matched = _role_allows(role, eff_action, eff_resource)
    if not allowed:
        # Try wildcard action/resource fallback: some roles use read:* pattern — we already handled "*" wildcards
        # No allow
        return PolicyDecision(
            False, f"RBAC deny: role '{role}' lacks {eff_action}:{eff_resource}", None
        )

    # ABAC — plant_id scoping
    # If resource has no plant scope, RBAC alone suffices
    if resource.plant_id is None:
        return PolicyDecision(True, f"RBAC allow: {role} → {eff_action}:{eff_resource}", matched)

    # System role may have cross-plant wildcard via extra
    extra_plant_ids = principal.extra.get("plant_ids") if principal.extra else None
    if extra_plant_ids == ["*"]:
        return PolicyDecision(True, f"ABAC allow: cross-plant wildcard for {role}", matched)

    # Strict equality
    if principal.plant_id != resource.plant_id:
        return PolicyDecision(
            False,
            f"ABAC deny: principal plant '{principal.plant_id}' != resource plant '{resource.plant_id}'",
            matched,
        )

    return PolicyDecision(
        True, f"allow: {role} → {eff_action}:{eff_resource} @ plant {resource.plant_id}", matched
    )
