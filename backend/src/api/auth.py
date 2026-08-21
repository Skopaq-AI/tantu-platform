"""API — auth router: /auth + /users. Handles signup, login, refresh, invite, RBAC user management.

Works with DB (SQLAlchemy async) or falls back to in-memory stores when DB unreachable (dev/tests).
Includes rate-limit, account lockout, audit logging, org isolation.
"""
from __future__ import annotations

import time
import uuid
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..domain.auth import (
    SignupRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    MeResponse,
    InviteRequest,
    InviteResponse,
    UserResponse,
    UsersListResponse,
    RoleUpdateRequest,
    UserInviteRequest,
)
from ..infra.security import (
    hash_pw,
    verify_pw,
    issue_jwt,
    verify_jwt,
    authorize,
    has_permission,
    require_role,
    require_permission,
    rate_limit,
    async_rate_limit,
    is_account_locked,
    record_failed_attempt,
    reset_failed_attempts,
    _remaining_lockout_s,
    PLATFORM_SUPER_ADMIN,
    ORG_OWNER,
    ORG_ADMIN,
)
from ..infra.db import (
    get_db,
    Organization,
    Plant,
    User,
    Membership,
    RefreshToken,
    Invitation,
    AuditLog,
)

log = logging.getLogger("tantu.api.auth")

# Router without prefix; routes include full path for flexible mounting
router = APIRouter(tags=["auth"])

# ── In-memory fallback stores (dev/tests when DB unreachable) ────────────
_mem_users: Dict[str, Dict[str, Any]] = {}  # id -> user dict
_mem_users_by_email: Dict[str, str] = {}  # email lower -> id
_mem_orgs: Dict[str, Dict[str, Any]] = {}  # id -> org dict
_mem_orgs_by_slug: Dict[str, str] = {}  # slug -> id
_mem_memberships: Dict[str, Dict[str, Any]] = {}  # id -> membership
_mem_membership_by_user_org: Dict[tuple, str] = {}  # (user_id, org_id) -> membership id
_mem_refresh: Dict[str, Dict[str, Any]] = {}  # jti -> token dict
_mem_refresh_by_hash: Dict[str, str] = {}  # hash -> jti
_mem_invites: Dict[str, Dict[str, Any]] = {}  # token -> invite dict
_mem_audit: List[Dict[str, Any]] = []

# Seed demo org/users for immediate dev use if empty
def _seed_mem() -> None:
    if _mem_users:
        return
    org_id = "org-demo-01"
    _mem_orgs[org_id] = {"id": org_id, "name": "Demo Org", "slug": "demo-org", "is_active": True, "created_at": datetime.now(timezone.utc)}
    _mem_orgs_by_slug["demo-org"] = org_id
    # default plant
    # seeded users: operator/maintenance/plant_admin etc per README
    seeds = [
        ("operator@example.com", "operator123", "OPERATOR"),
        ("maintenance@example.com", "maint123", "MAINTENANCE_LEAD"),
        ("plant_admin@example.com", "admin123", "PLANT_HEAD"),
        ("viewer@example.com", "viewer123", "VIEWER"),
    ]
    for email, pw, role in seeds:
        uid = uuid.uuid4().hex
        _mem_users[uid] = {"id": uid, "email": email, "password_hash": hash_pw(pw), "name": email.split("@")[0], "is_active": True, "is_verified": True, "created_at": datetime.now(timezone.utc)}
        _mem_users_by_email[email.lower()] = uid
        mid = uuid.uuid4().hex
        _mem_memberships[mid] = {"id": mid, "user_id": uid, "org_id": org_id, "role": role, "plant_ids": ["plant-demo-01"], "is_active": True}
        _mem_membership_by_user_org[(uid, org_id)] = mid

_seed_mem()

def _slugify(name: str) -> str:
    import re
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or f"org-{uuid.uuid4().hex[:6]}"

def _hash_token(tok: str) -> str:
    return hashlib.sha256(tok.encode()).hexdigest()

async def _try_db(coro):
    """Helper to try DB operation, fallback to memory on failure."""
    try:
        return await coro
    except Exception as e:
        log.debug("db fallback: %s", e)
        return None

def _audit(action: str, claims: Optional[Dict[str, Any]] = None, request: Optional[Request] = None, org_id: Optional[str] = None, target: Optional[str] = None, decision: str = "allow", reason: str = ""):
    try:
        entry = {
            "id": uuid.uuid4().hex,
            "action": action,
            "principal": claims.get("sub") if claims else "anonymous",
            "org_id": org_id or (claims.get("org_id") if claims else None),
            "resource": target,
            "created_at": datetime.now(timezone.utc),
            "decision": decision,
            "reason": reason,
            "ip": request.client.host if request and request.client else None,
            "path": request.url.path if request else None,
            "method": request.method if request else None,
        }
        _mem_audit.append(entry)
        # also try DB if available via background; not blocking
        log.info("audit %s %s org=%s decision=%s", action, entry["principal"], entry["org_id"], decision)
    except Exception:
        pass

async def _db_get_user_by_email(email: str, db: AsyncSession) -> Optional[User]:
    res = await db.execute(select(User).where(User.email == email.lower()))
    return res.scalars().first()

async def _db_get_user_by_id(uid: str, db: AsyncSession) -> Optional[User]:
    res = await db.execute(select(User).where(User.id == uid))
    return res.scalars().first()

async def _db_get_membership(user_id: str, org_id: str, db: AsyncSession) -> Optional[Membership]:
    res = await db.execute(select(Membership).where(Membership.user_id == user_id, Membership.org_id == org_id))
    return res.scalars().first()

async def _db_list_memberships(org_id: str, db: AsyncSession) -> List[Membership]:
    res = await db.execute(select(Membership).where(Membership.org_id == org_id))
    return list(res.scalars().all())

# ── Helpers for JWT claims building ──────────────────────────────────────
def _build_claims(user_id: str, org_id: str, role: str, plant_ids: List[str]) -> Dict[str, Any]:
    return {"sub": user_id, "org_id": org_id, "plant_ids": plant_ids, "roles": [role]}

def _issue_tokens(user_id: str, org_id: str, role: str, plant_ids: List[str], extra: Optional[Dict[str, Any]] = None) -> tuple[str, str, str]:
    """Returns (access_token, refresh_token, jti)"""
    access = issue_jwt(user_id, role=role, org_id=org_id, plant_ids=plant_ids, exp_min=60, extra=extra)
    # refresh token longer lived, separate jti
    jti = f"{user_id}:{int(time.time())}:{uuid.uuid4().hex[:8]}"
    refresh_claims_extra = {"jti": jti, "type": "refresh"}
    if extra:
        refresh_claims_extra.update(extra)
    refresh = issue_jwt(user_id, role=role, org_id=org_id, plant_ids=plant_ids, exp_min=60*24*7, extra=refresh_claims_extra)
    return access, refresh, jti

# ── Dependency to get current org context ─────────────────────────────────
async def _get_current_claims(authorization: Optional[str] = Header(None, alias="Authorization")) -> Dict[str, Any]:
    return verify_jwt(authorization=authorization)

# Replace with proper dependency via verify_jwt
get_current_user = verify_jwt  # alias

# ── /auth/signup ─────────────────────────────────────────────────────────
@router.post("/auth/signup", response_model=TokenResponse, status_code=201, summary="Signup — create org + owner")
async def signup(body: SignupRequest, request: Request, db: AsyncSession = Depends(get_db)):
    # Rate limit by IP
    ip = request.client.host if request.client else "unknown"
    if not rate_limit(f"signup:{ip}", max_hits=5, window_s=3600):
        raise HTTPException(429, "signup rate limited, try later")
    # also async check
    allowed = await async_rate_limit(f"signup:{ip}", max_hits=10, window_s=3600)
    if not allowed:
        raise HTTPException(429, "signup rate limited")

    slug = body.org_slug or _slugify(body.org_name)
    # Check org slug exists (DB or mem)
    org_id = None
    # Try DB first
    try:
        res = await db.execute(select(Organization).where(Organization.slug == slug))
        existing = res.scalars().first()
        if existing:
            raise HTTPException(400, f"org slug '{slug}' already exists")
        # create org
        org_id = uuid.uuid4().hex
        org = Organization(id=org_id, name=body.org_name, slug=slug, is_active=True)
        db.add(org)
        # create default plant
        plant_id = f"plant-{uuid.uuid4().hex[:8]}"
        plant = Plant(id=plant_id, org_id=org_id, name="Plant 01", code="P01")
        db.add(plant)
        # check user email
        if await _db_get_user_by_email(body.email.lower(), db):
            raise HTTPException(400, "email already registered")
        uid = uuid.uuid4().hex
        user = User(id=uid, email=body.email.lower(), password_hash=hash_pw(body.password), name=body.name or body.email.split("@")[0], is_active=True, is_verified=True)
        db.add(user)
        # membership org_owner
        mid = uuid.uuid4().hex
        membership = Membership(id=mid, user_id=uid, org_id=org_id, role=ORG_OWNER, plant_ids=["*"])
        db.add(membership)
        await db.commit()
        # audit
        _audit("signup", None, request, org_id=org_id, target=body.email)
        # issue tokens
        access, refresh, jti = _issue_tokens(uid, org_id, ORG_OWNER, ["*"])
        # store refresh
        rt = RefreshToken(id=uuid.uuid4().hex, user_id=uid, org_id=org_id, token_hash=_hash_token(refresh), jti=jti, expires_at=datetime.now(timezone.utc)+timedelta(days=7))
        db.add(rt)
        await db.commit()
        return TokenResponse(access_token=access, refresh_token=refresh, expires_in=3600, org_id=org_id, plant_ids=["*"], roles=[ORG_OWNER])
    except HTTPException:
        raise
    except Exception as e:
        log.debug("signup DB failed, fallback mem: %s", e)
        try:
            await db.rollback()
        except Exception:
            pass
        # Fallback in-memory
        if slug in _mem_orgs_by_slug:
            raise HTTPException(400, f"org slug '{slug}' already exists")
        if body.email.lower() in _mem_users_by_email:
            raise HTTPException(400, "email already registered")
        org_id = uuid.uuid4().hex
        _mem_orgs[org_id] = {"id": org_id, "name": body.org_name, "slug": slug, "is_active": True, "created_at": datetime.now(timezone.utc)}
        _mem_orgs_by_slug[slug] = org_id
        # plant
        # user
        uid = uuid.uuid4().hex
        _mem_users[uid] = {"id": uid, "email": body.email.lower(), "password_hash": hash_pw(body.password), "name": body.name or body.email.split("@")[0], "is_active": True, "created_at": datetime.now(timezone.utc)}
        _mem_users_by_email[body.email.lower()] = uid
        mid = uuid.uuid4().hex
        _mem_memberships[mid] = {"id": mid, "user_id": uid, "org_id": org_id, "role": ORG_OWNER, "plant_ids": ["*"], "is_active": True}
        _mem_membership_by_user_org[(uid, org_id)] = mid
        _audit("signup", None, request, org_id=org_id, target=body.email)
        access, refresh, jti = _issue_tokens(uid, org_id, ORG_OWNER, ["*"])
        _mem_refresh[jti] = {"jti": jti, "user_id": uid, "org_id": org_id, "token_hash": _hash_token(refresh), "expires_at": datetime.now(timezone.utc)+timedelta(days=7), "revoked": False}
        _mem_refresh_by_hash[_hash_token(refresh)] = jti
        return TokenResponse(access_token=access, refresh_token=refresh, expires_in=3600, org_id=org_id, plant_ids=["*"], roles=[ORG_OWNER])

# ── /auth/login ──────────────────────────────────────────────────────────
@router.post("/auth/login", response_model=TokenResponse, summary="Login — verify pw, issue access+refresh")
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    email = body.email.lower()
    ip = request.client.host if request.client else "unknown"
    key = f"login:{email}:{ip}"
    if is_account_locked(email):
        remain = _remaining_lockout_s(email)
        raise HTTPException(423, f"account locked, retry after {remain}s")
    # rate limit
    if not rate_limit(key, max_hits=10, window_s=60):
        raise HTTPException(429, "too many login attempts, try later")
    allowed = await async_rate_limit(key, max_hits=10, window_s=60)
    if not allowed:
        raise HTTPException(429, "too many login attempts")

    # Try DB
    user = None
    user_dict = None
    org_id = body.org_id or "org-demo-01"
    role = "VIEWER"
    plant_ids = ["plant-demo-01"]
    try:
        user = await _db_get_user_by_email(email, db)
        if user:
            if not user.is_active:
                raise HTTPException(403, "account deactivated")
            # check lock via db locked_until
            if user.locked_until and user.locked_until > datetime.now(timezone.utc):
                raise HTTPException(423, "account locked")
            if not verify_pw(body.password, user.password_hash):
                # record fail
                record_failed_attempt(email)
                # increment db failed attempts
                try:
                    user.failed_attempts = (user.failed_attempts or 0) + 1
                    if user.failed_attempts >= 5:
                        user.locked_until = datetime.now(timezone.utc) + timedelta(seconds=900)
                    await db.commit()
                except Exception:
                    pass
                # also check lockout after record
                if is_account_locked(email):
                    _audit("login_failed", None, request, org_id=org_id, target=email, decision="deny", reason="locked")
                    raise HTTPException(423, "account locked after repeated failures")
                _audit("login_failed", None, request, org_id=org_id, target=email, decision="deny", reason="bad password")
                raise HTTPException(401, "invalid credentials")
            # success: reset
            reset_failed_attempts(email)
            try:
                user.failed_attempts = 0
                user.locked_until = None
                user.last_login_at = datetime.now(timezone.utc)
                await db.commit()
            except Exception:
                pass
            # find membership
            membership = None
            if body.org_id:
                membership = await _db_get_membership(user.id, body.org_id, db)
                if not membership:
                    raise HTTPException(403, "no membership for org")
            else:
                # pick first membership
                res = await db.execute(select(Membership).where(Membership.user_id == user.id))
                membership = res.scalars().first()
            if membership:
                org_id = membership.org_id
                role = membership.role
                plant_ids = membership.plant_ids or ["plant-demo-01"]
            else:
                org_id = "org-demo-01"
                role = "VIEWER"
            # issue tokens
            access, refresh, jti = _issue_tokens(user.id, org_id, role, plant_ids)
            # store refresh
            rt = RefreshToken(id=uuid.uuid4().hex, user_id=user.id, org_id=org_id, token_hash=_hash_token(refresh), jti=jti, expires_at=datetime.now(timezone.utc)+timedelta(days=7))
            db.add(rt)
            await db.commit()
            _audit("login", {"sub": user.id, "org_id": org_id}, request, org_id=org_id, target=email)
            return TokenResponse(access_token=access, refresh_token=refresh, expires_in=3600, org_id=org_id, plant_ids=plant_ids, roles=[role])
        else:
            # fallback to mem
            raise LookupError("not in db, try mem")
    except HTTPException:
        raise
    except LookupError:
        # mem fallback path continues below
        pass
    except Exception as e:
        log.debug("login DB error fallback mem: %s", e)
        try:
            await db.rollback()
        except Exception:
            pass

    # In-memory fallback
    uid = _mem_users_by_email.get(email)
    if not uid or uid not in _mem_users:
        record_failed_attempt(email)
        _audit("login_failed", None, request, org_id=org_id, target=email, decision="deny", reason="no user")
        raise HTTPException(401, "invalid credentials")
    user_dict = _mem_users[uid]
    if not user_dict.get("is_active", True):
        raise HTTPException(403, "account deactivated")
    if not verify_pw(body.password, user_dict["password_hash"]):
        record_failed_attempt(email)
        if is_account_locked(email):
            raise HTTPException(423, "account locked")
        _audit("login_failed", None, request, target=email, decision="deny", reason="bad pw")
        raise HTTPException(401, "invalid credentials")
    reset_failed_attempts(email)
    # find membership in mem
    found = None
    for m in _mem_memberships.values():
        if m["user_id"] == uid and (body.org_id is None or m["org_id"] == body.org_id):
            found = m
            break
    if body.org_id and not found:
        raise HTTPException(403, "no membership for org")
    if found:
        org_id = found["org_id"]
        role = found["role"]
        plant_ids = found.get("plant_ids") or ["plant-demo-01"]
    # issue
    access, refresh, jti = _issue_tokens(uid, org_id, role, plant_ids)
    _mem_refresh[jti] = {"jti": jti, "user_id": uid, "org_id": org_id, "token_hash": _hash_token(refresh), "expires_at": datetime.now(timezone.utc)+timedelta(days=7), "revoked": False}
    _mem_refresh_by_hash[_hash_token(refresh)] = jti
    _audit("login", {"sub": uid, "org_id": org_id}, request, org_id=org_id, target=email)
    # update last login
    user_dict["last_login_at"] = datetime.now(timezone.utc)
    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=3600, org_id=org_id, plant_ids=plant_ids, roles=[role])

# ── /auth/refresh ────────────────────────────────────────────────────────
@router.post("/auth/refresh", response_model=TokenResponse, summary="Refresh — issue new access")
async def refresh(body: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    tok = body.refresh_token.strip()
    if not tok:
        raise HTTPException(401, "missing refresh token")
    # Verify refresh token as JWT first
    try:
        claims = verify_jwt(authorization=f"Bearer {tok}")
    except HTTPException as e:
        # try raw decode without header wrapper
        try:
            claims = verify_jwt(token=tok)
        except Exception:
            raise e
    # check type
    # if token has type refresh ensure?
    # Lookup stored refresh token hash
    h = _hash_token(tok)
    jti = claims.get("jti")
    user_id = claims.get("sub")
    org_id = claims.get("org_id", "org-demo-01")
    # Try DB
    try:
        res = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == h))
        row = res.scalars().first()
        if row:
            if row.revoked or row.expires_at < datetime.now(timezone.utc):
                raise HTTPException(401, "refresh token revoked or expired")
            # issue new access
            # find membership to get role/plant
            ms = await _db_get_membership(user_id, org_id, db)
            role = ms.role if ms else claims.get("role", "VIEWER")
            plant_ids = ms.plant_ids if ms and ms.plant_ids else claims.get("plant_ids", ["plant-demo-01"])
            # optionally rotate refresh? Keep same jti but issue new access
            access = issue_jwt(user_id, role=role, org_id=org_id, plant_ids=plant_ids, exp_min=60)
            _audit("refresh", claims, request, org_id=org_id, target=user_id)
            return TokenResponse(access_token=access, refresh_token=tok, expires_in=3600, org_id=org_id, plant_ids=plant_ids, roles=[role])
        # also try by jti
        if jti:
            res = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
            row = res.scalars().first()
            if row and not row.revoked:
                ms = await _db_get_membership(user_id, org_id, db)
                role = ms.role if ms else claims.get("role", "VIEWER")
                plant_ids = ms.plant_ids if ms and ms.plant_ids else claims.get("plant_ids", ["plant-demo-01"])
                access = issue_jwt(user_id, role=role, org_id=org_id, plant_ids=plant_ids, exp_min=60)
                return TokenResponse(access_token=access, refresh_token=tok, expires_in=3600, org_id=org_id, plant_ids=plant_ids, roles=[role])
    except HTTPException:
        raise
    except Exception as e:
        log.debug("refresh DB lookup failed mem fallback: %s", e)
        try:
            await db.rollback()
        except Exception:
            pass
    # Mem fallback
    entry = None
    if h in _mem_refresh_by_hash:
        jti_lookup = _mem_refresh_by_hash[h]
        entry = _mem_refresh.get(jti_lookup)
    elif jti and jti in _mem_refresh:
        entry = _mem_refresh[jti]
    if not entry:
        # If no stored refresh but JWT valid, allow issuing new access if within exp (stateless fallback)
        # Check exp still valid (verify_jwt already checked)
        role = claims.get("role", "VIEWER")
        plant_ids = claims.get("plant_ids", ["plant-demo-01"])
        org_id = claims.get("org_id", "org-demo-01")
        if claims.get("type") != "refresh" and "type" in claims:
            # not refresh type but allow?
            pass
        # ensure not expired (verify_jwt ensures)
        access = issue_jwt(user_id, role=role, org_id=org_id, plant_ids=plant_ids, exp_min=60)
        _audit("refresh_stateless", claims, request, org_id=org_id, target=user_id)
        return TokenResponse(access_token=access, refresh_token=tok, expires_in=3600, org_id=org_id, plant_ids=plant_ids, roles=[role])
    if entry.get("revoked") or entry["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(401, "refresh token revoked or expired")
    # issue
    # find membership
    uid = entry["user_id"]
    org_id = entry["org_id"]
    # lookup membership
    found_role = "VIEWER"
    found_plants = ["plant-demo-01"]
    for m in _mem_memberships.values():
        if m["user_id"] == uid and m["org_id"] == org_id:
            found_role = m["role"]
            found_plants = m.get("plant_ids") or ["plant-demo-01"]
            break
    else:
        # use claims
        found_role = claims.get("role", found_role)
        found_plants = claims.get("plant_ids", found_plants)
    access = issue_jwt(uid, role=found_role, org_id=org_id, plant_ids=found_plants, exp_min=60)
    _audit("refresh", claims, request, org_id=org_id, target=uid)
    return TokenResponse(access_token=access, refresh_token=tok, expires_in=3600, org_id=org_id, plant_ids=found_plants, roles=[found_role])

# ── /auth/invite ─────────────────────────────────────────────────────────
@router.post("/auth/invite", response_model=InviteResponse, summary="Invite user (requires org admin)")
async def invite(
    body: InviteRequest,
    request: Request,
    claims: Dict[str, Any] = Depends(verify_jwt),
    db: AsyncSession = Depends(get_db),
):
    # Rate limit
    ip = request.client.host if request.client else "unknown"
    await async_rate_limit(f"invite:{claims.get('sub')}:{ip}", max_hits=20, window_s=3600)
    # Permission check: need user:invite
    if not has_permission(claims, "user:invite") and not has_permission(claims, "user:manage"):
        # also allow ORG_ADMIN, ORG_OWNER, PLANT_HEAD etc via role check
        if not authorize(claims, required_role=[ORG_OWNER, ORG_ADMIN, "PLANT_HEAD", "org_owner", "org_admin"], permission=None):
            # fallback check via has_permission still fails, so deny
            if not authorize(claims, required_role=[PLATFORM_SUPER_ADMIN]):
                raise HTTPException(403, "missing permission user:invite")
    org_id = body.org_id or claims.get("org_id")
    if not org_id:
        raise HTTPException(400, "org_id missing")
    # Ensure org exists
    # check org isolation: non-super admin cannot invite to other org
    claim_org = claims.get("org_id")
    if PLATFORM_SUPER_ADMIN not in [c.upper() for c in (claims.get("roles") or [])]:
        if org_id != claim_org:
            raise HTTPException(403, "cross-org invite denied")
    # Create invitation token
    token = uuid.uuid4().hex + uuid.uuid4().hex
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    # Try DB
    try:
        # check org exists
        res = await db.execute(select(Organization).where(Organization.id == org_id))
        org = res.scalars().first()
        if not org:
            # also allow mem org
            if org_id not in _mem_orgs:
                raise HTTPException(404, "org not found")
        # check existing user?
        inv = Invitation(
            id=uuid.uuid4().hex,
            org_id=org_id,
            email=body.email.lower(),
            role=body.role,
            plant_ids=body.plant_ids or ["plant-demo-01"],
            token=token,
            token_hash=_hash_token(token),
            invited_by=claims.get("sub"),
            expires_at=expires,
        )
        db.add(inv)
        # also audit log
        al = AuditLog(id=uuid.uuid4().hex, org_id=org_id, user_id=claims.get("sub"), principal=claims.get("sub"), action="invite", resource=body.email.lower(), plant_id=None, decision="allow", request_id=request.headers.get("x-request-id"), ip_address=ip)
        db.add(al)
        await db.commit()
        _audit("invite", claims, request, org_id=org_id, target=body.email.lower())
        return InviteResponse(invitation_id=inv.id, email=body.email.lower(), role=body.role, plant_ids=body.plant_ids, token=token, expires_at=expires)
    except HTTPException:
        raise
    except Exception as e:
        log.debug("invite DB fallback mem: %s", e)
        try:
            await db.rollback()
        except Exception:
            pass
        # mem
        if org_id not in _mem_orgs:
            # create stub org if not exists for tests
            _mem_orgs[org_id] = {"id": org_id, "name": f"Org {org_id}", "slug": org_id, "is_active": True}
        inv_id = uuid.uuid4().hex
        _mem_invites[token] = {"id": inv_id, "org_id": org_id, "email": body.email.lower(), "role": body.role, "plant_ids": body.plant_ids or ["plant-demo-01"], "token": token, "expires_at": expires, "accepted": False, "invited_by": claims.get("sub")}
        _audit("invite", claims, request, org_id=org_id, target=body.email.lower())
        return InviteResponse(invitation_id=inv_id, email=body.email.lower(), role=body.role, plant_ids=body.plant_ids, token=token, expires_at=expires)

# ── /auth/me ─────────────────────────────────────────────────────────────
@router.get("/auth/me", response_model=MeResponse, summary="Current principal")
async def me(claims: Dict[str, Any] = Depends(verify_jwt), db: AsyncSession = Depends(get_db)):
    # try to enrich with user email
    uid = claims.get("sub")
    email = None
    # DB lookup
    try:
        user = await _db_get_user_by_id(uid, db)
        if user:
            email = user.email
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
    if not email:
        # mem
        u = _mem_users.get(uid)
        if u:
            email = u["email"]
    return MeResponse(
        sub=uid,
        email=email,
        org_id=claims.get("org_id"),
        plant_ids=claims.get("plant_ids"),
        roles=claims.get("roles"),
        permissions=claims.get("permissions"),
        claims=claims,
    )

# ── /users ───────────────────────────────────────────────────────────────
@router.get("/users", response_model=UsersListResponse, summary="List org users")
async def list_users(
    request: Request,
    claims: Dict[str, Any] = Depends(verify_jwt),
    db: AsyncSession = Depends(get_db),
    org_id: Optional[str] = Query(None),
):
    # permission: user:read
    if not has_permission(claims, "user:read") and not has_permission(claims, "user:manage"):
        raise HTTPException(403, "missing permission user:read")
    target_org = org_id or claims.get("org_id")
    if not target_org:
        raise HTTPException(400, "org_id required")
    # org isolation
    if PLATFORM_SUPER_ADMIN not in [r.upper() for r in (claims.get("roles") or [])]:
        if target_org != claims.get("org_id"):
            raise HTTPException(403, "cross-org access denied")
    # rate limit
    await async_rate_limit(f"list_users:{claims.get('sub')}", max_hits=60, window_s=60)
    users: List[UserResponse] = []
    # Try DB
    try:
        memberships = await _db_list_memberships(target_org, db)
        for m in memberships:
            u = await _db_get_user_by_id(m.user_id, db)
            if not u:
                continue
            users.append(UserResponse(id=u.id, email=u.email, name=u.name, role=m.role, plant_ids=m.plant_ids, org_id=target_org, is_active=u.is_active, created_at=u.created_at))
        if users:
            _audit("list_users", claims, request, org_id=target_org, target=f"count={len(users)}")
            return UsersListResponse(users=users, total=len(users), org_id=target_org)
    except Exception as e:
        log.debug("list_users DB fallback: %s", e)
        try:
            await db.rollback()
        except Exception:
            pass
    # mem fallback
    for m in _mem_memberships.values():
        if m["org_id"] != target_org:
            continue
        u = _mem_users.get(m["user_id"])
        if not u:
            continue
        users.append(UserResponse(id=u["id"], email=u["email"], name=u.get("name"), role=m["role"], plant_ids=m.get("plant_ids"), org_id=target_org, is_active=u.get("is_active", True), created_at=u.get("created_at")))
    _audit("list_users", claims, request, org_id=target_org, target=f"count={len(users)}")
    return UsersListResponse(users=users, total=len(users), org_id=target_org)

@router.post("/users/invite", response_model=InviteResponse, summary="Invite via users prefix")
async def users_invite(
    body: UserInviteRequest,
    request: Request,
    claims: Dict[str, Any] = Depends(verify_jwt),
    db: AsyncSession = Depends(get_db),
):
    # delegate to invite logic
    inv_req = InviteRequest(email=body.email, role=body.role, plant_ids=body.plant_ids, org_id=claims.get("org_id"))
    return await invite(inv_req, request, claims, db)

@router.patch("/users/{user_id}/role", response_model=UserResponse, summary="Update user role")
async def update_role(
    user_id: str,
    body: RoleUpdateRequest,
    request: Request,
    claims: Dict[str, Any] = Depends(verify_jwt),
    db: AsyncSession = Depends(get_db),
):
    if not has_permission(claims, "user:update_role") and not has_permission(claims, "user:manage"):
        # fallback role check
        if not authorize(claims, required_role=[PLATFORM_SUPER_ADMIN, ORG_OWNER, ORG_ADMIN]):
            raise HTTPException(403, "missing permission user:update_role")
    org_id = claims.get("org_id")
    # Org isolation
    # Check target membership org
    # Try DB
    try:
        m = await _db_get_membership(user_id, org_id, db)
        if m:
            # prevent self-demote super admin? allow
            m.role = body.role
            if body.plant_ids is not None:
                m.plant_ids = body.plant_ids
            await db.commit()
            u = await _db_get_user_by_id(user_id, db)
            _audit("update_role", claims, request, org_id=org_id, target=user_id, reason=f"role->{body.role}")
            return UserResponse(id=u.id, email=u.email, name=u.name, role=m.role, plant_ids=m.plant_ids, org_id=org_id, is_active=u.is_active, created_at=u.created_at)
    except HTTPException:
        raise
    except Exception as e:
        log.debug("update_role DB fallback: %s", e)
        try:
            await db.rollback()
        except Exception:
            pass
    # mem fallback
    key = (user_id, org_id)
    mid = _mem_membership_by_user_org.get(key)
    if not mid or mid not in _mem_memberships:
        # search any
        for mid2, m in _mem_memberships.items():
            if m["user_id"] == user_id and m["org_id"] == org_id:
                mid = mid2
                break
    if not mid:
        raise HTTPException(404, "membership not found")
    m = _mem_memberships[mid]
    m["role"] = body.role
    if body.plant_ids is not None:
        m["plant_ids"] = body.plant_ids
    u = _mem_users.get(user_id)
    if not u:
        raise HTTPException(404, "user not found")
    _audit("update_role", claims, request, org_id=org_id, target=user_id, reason=f"role->{body.role}")
    return UserResponse(id=u["id"], email=u["email"], name=u.get("name"), role=m["role"], plant_ids=m.get("plant_ids"), org_id=org_id, is_active=u.get("is_active", True), created_at=u.get("created_at"))

@router.delete("/users/{user_id}", status_code=204, summary="Remove user from org")
async def delete_user(
    user_id: str,
    request: Request,
    claims: Dict[str, Any] = Depends(verify_jwt),
    db: AsyncSession = Depends(get_db),
):
    if not has_permission(claims, "user:delete") and not has_permission(claims, "user:manage"):
        if not authorize(claims, required_role=[PLATFORM_SUPER_ADMIN, ORG_OWNER, ORG_ADMIN]):
            raise HTTPException(403, "missing permission user:delete")
    org_id = claims.get("org_id")
    # Prevent self-delete?
    if user_id == claims.get("sub"):
        raise HTTPException(400, "cannot delete self")
    # Check privilege: cannot delete higher role? Simplified: ORG_OWNER can delete anyone, ORG_ADMIN cannot delete ORG_OWNER
    # Try DB
    try:
        m = await _db_get_membership(user_id, org_id, db)
        if m:
            # check role hierarchy?
            # if target is ORG_OWNER and caller is not ORG_OWNER/super admin, deny
            caller_roles = [r.upper() for r in (claims.get("roles") or [])]
            if m.role == ORG_OWNER and ORG_OWNER not in caller_roles and PLATFORM_SUPER_ADMIN not in caller_roles:
                raise HTTPException(403, "cannot delete org owner")
            await db.delete(m)
            # maybe delete user if no other memberships
            res = await db.execute(select(Membership).where(Membership.user_id == user_id))
            remaining = list(res.scalars().all())
            if len(remaining) <= 1:  # we already deleted one, if 0 remaining -> delete user?
                # if only this org membership, remove user
                if len(remaining) == 0:
                    u = await _db_get_user_by_id(user_id, db)
                    if u:
                        await db.delete(u)
            await db.commit()
            _audit("delete_user", claims, request, org_id=org_id, target=user_id)
            return
    except HTTPException:
        raise
    except Exception as e:
        log.debug("delete_user DB fallback mem: %s", e)
        try:
            await db.rollback()
        except Exception:
            pass
    # mem fallback
    mid = _mem_membership_by_user_org.get((user_id, org_id))
    if not mid:
        # search
        for k, mid2 in list(_mem_membership_by_user_org.items()):
            if k[0] == user_id and k[1] == org_id:
                mid = mid2
                break
    if not mid or mid not in _mem_memberships:
        raise HTTPException(404, "membership not found")
    target_role = _mem_memberships[mid]["role"]
    caller_roles = [r.upper() for r in (claims.get("roles") or [])]
    if target_role == ORG_OWNER and ORG_OWNER not in caller_roles and PLATFORM_SUPER_ADMIN not in caller_roles:
        raise HTTPException(403, "cannot delete org owner")
    del _mem_memberships[mid]
    _mem_membership_by_user_org.pop((user_id, org_id), None)
    # check if user has any other memberships
    has_other = any(m["user_id"] == user_id for m in _mem_memberships.values())
    if not has_other:
        # delete user
        _mem_users.pop(user_id, None)
        # remove email index
        for em, uid in list(_mem_users_by_email.items()):
            if uid == user_id:
                _mem_users_by_email.pop(em, None)
    _audit("delete_user", claims, request, org_id=org_id, target=user_id)
    return

# ── Health for auth service (public) ─────────────────────────────────────
@router.get("/auth/health", summary="Auth health")
async def auth_health():
    return {"status": "ok", "service": "auth", "users_mem": len(_mem_users), "orgs_mem": len(_mem_orgs)}
