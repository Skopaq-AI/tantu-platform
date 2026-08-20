"""JWT auth — mirrors backend/src/infra/security.py (HS256, dev key fallback)."""
from __future__ import annotations

import os
import time
from typing import Optional

from fastapi import Depends, HTTPException, Header, status
from jose import JWTError, jwt

ALG = "HS256"
SECRET = os.getenv("JWT_PRIVATE_KEY", "dev-only-key-replace-in-prod")
ISSUER = os.getenv("JWT_ISSUER", "tantu")


def issue_jwt(sub: str, plant_id: str, role: str, exp_min: int = 60) -> str:
    now = int(time.time())
    payload = {"sub": sub, "plant_id": plant_id, "role": role, "exp": now + exp_min * 60, "iat": now, "iss": ISSUER}
    return jwt.encode(payload, SECRET, algorithm=ALG)


def verify_jwt(token: str) -> dict:
    return jwt.decode(token, SECRET, algorithms=[ALG], options={"verify_aud": False})


def authorize(claims: dict, required_role: str, plant_id: str) -> bool:
    role = claims.get("role", "")
    if role != required_role and role != "plant_admin":
        return False
    return claims.get("plant_id") == plant_id


async def require_auth(authorization: Optional[str] = Header(None)) -> dict:
    """FastAPI dependency — validates Bearer token. Raises 401 if invalid."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        claims = verify_jwt(token)
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}") from e
    # exp is validated by jose; ensure required claims
    if "sub" not in claims or "plant_id" not in claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing required claims")
    return claims


async def optional_auth(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        return None
    try:
        return verify_jwt(authorization.removeprefix("Bearer ").strip())
    except JWTError:
        return None
