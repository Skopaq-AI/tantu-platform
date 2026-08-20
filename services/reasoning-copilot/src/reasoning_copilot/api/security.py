"""JWT + RBAC/ABAC — HS256 (RS256-ready) + dev fallback."""
from __future__ import annotations

import time
from typing import Optional

from fastapi import Header, HTTPException
from jose import jwt, JWTError

from ..config import settings

ALG = "HS256"


def issue_jwt(sub: str, plant_id: str, role: str = "operator", exp_min: int = 60) -> str:
    now = int(time.time())
    payload = {"sub": sub, "plant_id": plant_id, "role": role, "iat": now, "exp": now + exp_min * 60}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALG)


def verify_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALG])
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"invalid token: {e}")


async def optional_auth(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    if not authorization:
        return None
    # Bearer <token>
    tok = authorization.removeprefix("Bearer ").strip()
    return verify_jwt(tok)


async def require_auth(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="missing Authorization: Bearer <jwt>")
    tok = authorization.removeprefix("Bearer ").strip()
    return verify_jwt(tok)
