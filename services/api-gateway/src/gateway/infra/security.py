"""JWT RS256 verify — real cryptography, OPA inputs, with safe dev fallback.

Primary: RS256 verify against PEM public key from JWT_PUBLIC_KEY.
Fallback: HS256 using JWT_PRIVATE_KEY when RS256 not configured — logs warning.

Also provides token issuance for dev/tests and FastAPI dependencies.
"""
from __future__ import annotations

import time
import logging
from typing import Optional, Any

from fastapi import Depends, Header, HTTPException, status
from jose import jwt, JWTError
from pydantic import BaseModel

from .config import settings

log = logging.getLogger("gateway.security")

# ── Key handling ─────────────────────────────────────────────────────

def _normalize_pem(pem: str) -> str:
    """Support escaped newlines (env var with \\n)."""
    if not pem:
        return ""
    # Handle literal \n
    if "\\n" in pem:
        pem = pem.replace("\\n", "\n")
    return pem.strip()


def _load_verify_keys() -> tuple[str, str, str]:
    """Return (algorithm, verify_key, sign_key_pem_or_secret)."""
    pub = _normalize_pem(settings.jwt_public_key)
    priv = _normalize_pem(settings.jwt_private_key)
    algo = settings.jwt_algorithm.upper()

    # If RS256 requested but no public key configured → fallback
    if algo == "RS256" and pub and "BEGIN PUBLIC KEY" in pub:
        return "RS256", pub, priv  # priv may be used for issuing; verify uses pub
    if algo == "RS256" and priv and "BEGIN PRIVATE KEY" in priv:
        # Derive public from private for verify (dev): if only private given we can still verify HS fallback is not needed.
        # Try to derive public key via cryptography
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend
            private_key = serialization.load_pem_private_key(priv.encode(), password=None, backend=default_backend())
            public_key = private_key.public_key()
            pub_derived = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode()
            log.warning("gateway RS256: derived PUBLIC KEY from PRIVATE KEY (dev only)")
            return "RS256", pub_derived, priv
        except Exception as e:
            log.warning("gateway RS256 derive failed, falling back to HS256: %s", e)

    if algo == "RS256" and not pub:
        log.warning(
            "gateway RS256 requested but JWT_PUBLIC_KEY not set — falling back to HS256 (dev only). "
            "Set JWT_PUBLIC_KEY in production."
        )
        return "HS256", priv, priv

    if algo == "HS256":
        return "HS256", priv, priv

    # Unknown algo → fallback HS256
    log.warning("gateway unknown JWT alg %s, using HS256 fallback", algo)
    return "HS256", priv, priv


_ALG, _VERIFY_KEY, _SIGN_KEY = _load_verify_keys()

# For test convenience: allow resetting keys at runtime
def _get_verify_state() -> tuple[str, str, str]:
    return _load_verify_keys()


# ── JWT issue / verify ───────────────────────────────────────────────

def issue_jwt(
    sub: str,
    plant_id: str,
    role: str,
    exp_min: int = 60,
    extra: Optional[dict[str, Any]] = None,
    issuer: Optional[str] = None,
    audience: Optional[str] = None,
) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": sub,
        "plant_id": plant_id,
        "role": role,
        "iss": issuer or settings.jwt_issuer,
        "aud": audience or settings.jwt_audience,
        "iat": now,
        "exp": now + exp_min * 60,
        "jti": f"{sub}:{now}",
    }
    if extra:
        payload.update(extra)
    alg, _, sign_key = _get_verify_state()
    # For RS256 we need private key PEM; if only public is set we cannot sign → fallback HS256 for issue
    if alg == "RS256":
        if sign_key and "BEGIN PRIVATE KEY" in sign_key:
            return jwt.encode(payload, sign_key, algorithm="RS256")
        else:
            # fallback HS256 for dev token issuance
            log.warning("gateway issue_jwt: RS256 private key not available, issuing HS256 token")
            return jwt.encode(payload, settings.jwt_private_key, algorithm="HS256")
    return jwt.encode(payload, sign_key, algorithm=alg)


def verify_jwt(token: str) -> dict[str, Any]:
    """Verify and decode JWT — raises JWTError on failure."""
    alg, verify_key, _ = _get_verify_state()
    # Try primary alg first, then HS256 fallback for backward compat
    try:
        claims = jwt.decode(
            token,
            verify_key,
            algorithms=[alg],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"verify_aud": False},  # allow callers without aud for internal tokens
        )
        return claims
    except JWTError as e:
        # If RS256 failed, try HS256 as compat (existing tokens from older backend)
        if alg == "RS256":
            try:
                claims = jwt.decode(
                    token,
                    settings.jwt_private_key,
                    algorithms=["HS256"],
                    options={"verify_aud": False},
                )
                log.debug("gateway verify_jwt: accepted HS256 fallback token")
                return claims
            except JWTError:
                pass
        raise e


# ── Pydantic models ──────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


# ── FastAPI dependencies ─────────────────────────────────────────────

async def require_auth(authorization: Optional[str] = Header(None)) -> dict[str, Any]:
    """Mandatory auth — 401 if missing/invalid. Returns claims."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Empty token")
    try:
        claims = verify_jwt(token)
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}") from e
    if "sub" not in claims or "plant_id" not in claims or "role" not in claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing required claims (sub/plant_id/role)")
    # exp validated by jose
    return claims


async def optional_auth(authorization: Optional[str] = Header(None)) -> Optional[dict[str, Any]]:
    """Optional auth — returns None if absent, raises only on malformed valid-looking token? Returns None on invalid too."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        return None
    try:
        return verify_jwt(token)
    except JWTError:
        return None
