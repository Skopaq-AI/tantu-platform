"""Domain — auth Pydantic schemas (clean arch, no I/O)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, field_validator

# ── Enums / constants ────────────────────────────────────────────────────
ALLOWED_ROLES = [
    "PLATFORM_SUPER_ADMIN",
    "ORG_OWNER",
    "ORG_ADMIN",
    "PLANT_HEAD",
    "MAINTENANCE_LEAD",
    "MAINTENANCE_TECH",
    "OPERATOR",
    "VIEWER",
    "INTEGRATION_BOT",
]
# also allow lower case aliases for API convenience
ALLOWED_ROLES_LOWER = [r.lower() for r in ALLOWED_ROLES] + ["operator", "viewer", "maintenance", "plant_admin", "system"]

def _validate_role(v: str) -> str:
    if not v:
        raise ValueError("role required")
    # normalize
    up = v.upper()
    aliases = {
        "OPERATOR": "OPERATOR",
        "VIEWER": "VIEWER",
        "MAINTENANCE": "MAINTENANCE_LEAD",
        "PLANT_ADMIN": "PLANT_HEAD",
        "SYSTEM": "PLATFORM_SUPER_ADMIN",
    }
    if up in ALLOWED_ROLES:
        return up
    if up in aliases:
        return aliases[up]
    # try lower
    low = v.lower()
    if low in ["operator", "viewer", "maintenance", "plant_admin"]:
        return aliases[low.upper()]
    raise ValueError(f"invalid role '{v}'. allowed: {ALLOWED_ROLES}")

# ── Auth requests / responses ────────────────────────────────────────────

class SignupRequest(BaseModel):
    org_name: str = Field(..., min_length=2, max_length=255, description="Organization name")
    email: EmailStr = Field(..., description="Admin email")
    password: str = Field(..., min_length=8, max_length=128)
    name: Optional[str] = Field(None, max_length=255)
    org_slug: Optional[str] = Field(None, max_length=128, description="Optional slug; auto-derived if absent")

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)
    org_id: Optional[str] = Field(None, description="Optional org scoping for multi-tenant")

class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int = 3600
    org_id: Optional[str] = None
    plant_ids: Optional[List[str]] = None
    roles: Optional[List[str]] = None

class MeResponse(BaseModel):
    sub: str
    email: Optional[str] = None
    org_id: Optional[str] = None
    plant_ids: Optional[List[str]] = None
    roles: Optional[List[str]] = None
    permissions: Optional[List[str]] = None
    claims: Dict[str, Any] = Field(default_factory=dict)

class InviteRequest(BaseModel):
    email: EmailStr
    role: str = Field(..., description="Role to assign")
    plant_ids: Optional[List[str]] = Field(None, description="ABAC plant scope; null or ['*'] for wildcard")
    org_id: Optional[str] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        return _validate_role(v)

class InviteResponse(BaseModel):
    invitation_id: str
    email: EmailStr
    role: str
    plant_ids: Optional[List[str]] = None
    token: Optional[str] = None
    expires_at: Optional[datetime] = None

class UserCreateRequest(BaseModel):
    email: EmailStr
    password: Optional[str] = Field(None, min_length=8)
    name: Optional[str] = None
    role: str = "VIEWER"
    plant_ids: Optional[List[str]] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        return _validate_role(v)

class UserInviteRequest(BaseModel):
    email: EmailStr
    role: str = "VIEWER"
    plant_ids: Optional[List[str]] = None
    name: Optional[str] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        return _validate_role(v)

class RoleUpdateRequest(BaseModel):
    role: str
    plant_ids: Optional[List[str]] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        return _validate_role(v)

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: Optional[str] = None
    role: Optional[str] = None
    plant_ids: Optional[List[str]] = None
    org_id: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

class UsersListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    org_id: Optional[str] = None

class AuditLogEntry(BaseModel):
    id: str
    org_id: Optional[str] = None
    principal: Optional[str] = None
    action: str
    resource: Optional[str] = None
    plant_id: Optional[str] = None
    decision: Optional[str] = None
    reason: Optional[str] = None
    created_at: Optional[datetime] = None

# ── Generic error envelope ───────────────────────────────────────────────
class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
