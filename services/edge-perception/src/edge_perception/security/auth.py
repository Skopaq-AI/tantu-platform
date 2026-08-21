"""JWT auth — HS256 dev / RS256 prod compatible, matches backend contract."""

from __future__ import annotations

import os
import time
from fastapi import Header, HTTPException, status
from jose import JWTError, jwt

ALG_DEFAULT = "HS256"


def _secret_and_alg() -> tuple[str, str]:
    sec = os.getenv("JWT_SECRET", os.getenv("JWT_PRIVATE_KEY", "dev-only-key-replace-in-prod"))
    alg = os.getenv("JWT_ALGORITHM", ALG_DEFAULT)
    # if secret looks like PEM, use RS256
    if sec.strip().startswith("-----BEGIN"):
        alg = "RS256"
    return sec, alg


def issue_jwt(sub: str, plant_id: str, role: str, exp_min: int = 60) -> str:
    secret, alg = _secret_and_alg()
    now = int(time.time())
    payload = {
        "sub": sub,
        "plant_id": plant_id,
        "role": role,
        "exp": now + exp_min * 60,
        "iat": now,
    }
    return jwt.encode(payload, secret, algorithm=alg)


def verify_jwt(token: str) -> dict:
    secret, alg = _secret_and_alg()
    # support both HS256 and RS256 verify — try configured alg first, then HS256 fallback for dev
    for a in (alg, "HS256", "RS256"):
        try:
            return jwt.decode(token, secret, algorithms=[a])
        except JWTError:
            continue
    raise JWTError("invalid token")


class RBAC:
    """Dependency factory for role + plant scoping. Usage: Depends(RBAC('maintenance')) ."""

    def __init__(self, required_role: str | None = None) -> None:
        self.required_role = required_role

    async def __call__(self, authorization: str | None = Header(default=None)) -> dict:
        # allow open access when JWT_SECRET is dev default and no header — for edge/demo convenience,
        # but enforce when header is present.
        if not authorization:
            # if caller wants auth, they must send it; if not, allow anonymous with limited role
            # To keep secure-by-default, require auth on protected routes via explicit Depends.
            # This callable itself, when used as dependency, REQUIRES a token.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token"
            )
        token = authorization.removeprefix("Bearer ").strip()
        try:
            claims = verify_jwt(token)
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=f"invalid token: {e}"
            )
        if self.required_role and claims.get("role") not in (
            self.required_role,
            "plant_admin",
            "admin",
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
        return claims


async def require_auth(authorization: str | None = Header(default=None)) -> dict | None:
    """Optional auth — returns claims if token present, else None (for open telemetry endpoints)."""
    if not authorization:
        return None
    token = authorization.removeprefix("Bearer ").strip()
    try:
        return verify_jwt(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
