"""Security — OWASP ASVS patterns, minimal but production-shaped."""
import time, os
from jose import jwt
from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALG = "RS256"  # in prod, load from Vault; here HS256 fallback for dev
SECRET = os.getenv("JWT_PRIVATE_KEY", "dev-only-key-replace-in-prod")

def hash_pw(p: str) -> str: return pwd.hash(p)
def verify_pw(p, h) -> bool: return pwd.verify(p, h)

def issue_jwt(sub: str, plant_id: str, role: str, exp_min=60) -> str:
    payload = {"sub": sub, "plant_id": plant_id, "role": role, "exp": int(time.time())+exp_min*60, "iat": int(time.time())}
    return jwt.encode(payload, SECRET, algorithm="HS256")

def verify_jwt(tok: str) -> dict:
    return jwt.decode(tok, SECRET, algorithms=["HS256"])

# RBAC + ABAC stub
def authorize(claims: dict, required_role: str, plant_id: str) -> bool:
    if claims.get("role") != required_role and claims.get("role") != "plant_admin":
        return False
    # ABAC: plant_id must match
    return claims.get("plant_id") == plant_id

# Rate limit stub (use Redis in prod)
from collections import defaultdict
_hits = defaultdict(list)
def rate_limit(key: str, max_hits=30, window_s=60) -> bool:
    now = time.time()
    _hits[key] = [t for t in _hits[key] if now - t < window_s]
    _hits[key].append(now)
    return len(_hits[key]) <= max_hits
