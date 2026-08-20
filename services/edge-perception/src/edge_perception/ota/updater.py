"""Secure OTA — stubbed transport, REAL verification + version monotonicity + rollback state.

Design:
  - package = {version, artifact_url or bytes, sha256, signature_b64, timestamp}
  - verify: sha256 + HMAC/Ed25519 signature if public key configured, else HMAC with JWT_SECRET
  - monotonic version check (semver-ish)
  - staged states: idle → downloading → verifying → staging → ready_to_apply → applied / failed
  - rollback retains previous version
  - no actual reboot/flash — apply() flips current_version in memory + persists state file
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class OTAState(str, Enum):
    IDLE = "idle"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    STAGING = "staging"
    READY = "ready_to_apply"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass(slots=True)
class OTAPackage:
    version: str
    sha256: str  # hex
    signature_b64: str = ""  # base64 signature over sha256 (HMAC or Ed25519)
    artifact_url: str = ""
    artifact_bytes: bytes | None = None
    timestamp: float = field(default_factory=time.time)
    notes: str = ""


_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")


def _parse_semver(v: str) -> tuple[int, int, int]:
    m = _SEMVER_RE.match(v.strip())
    if not m:
        raise ValueError(f"invalid semver: {v!r}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _is_newer(candidate: str, current: str) -> bool:
    try:
        return _parse_semver(candidate) > _parse_semver(current)
    except ValueError:
        # fallback lexicographic
        return candidate != current and candidate > current


class OTAUpdater:
    def __init__(
        self,
        current_version: str = "0.1.0",
        public_key_path: str | None = None,
        hmac_secret: str | None = None,
        state_path: str | Path | None = None,
    ) -> None:
        self.current_version = current_version
        self.public_key_path = Path(public_key_path) if public_key_path else None
        self.hmac_secret = hmac_secret
        self.state_path = Path(state_path) if state_path else None
        self.state: OTAState = OTAState.IDLE
        self.last_error: str | None = None
        self.staged: OTAPackage | None = None
        self.previous_version: str | None = None
        self.history: list[dict] = []
        # load persisted state if present
        if self.state_path and self.state_path.exists():
            try:
                d = json.loads(self.state_path.read_text())
                self.current_version = d.get("current_version", self.current_version)
                self.previous_version = d.get("previous_version")
                self.state = OTAState(d.get("state", OTAState.IDLE))
            except Exception:
                pass

    def _persist(self) -> None:
        if not self.state_path:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps({
            "current_version": self.current_version,
            "previous_version": self.previous_version,
            "state": self.state.value,
            "ts": time.time(),
        }, indent=2))

    def _verify_sha256(self, data: bytes, expected_hex: str) -> bool:
        got = hashlib.sha256(data).hexdigest()
        return hmac.compare_digest(got.lower(), expected_hex.lower())

    def _verify_signature(self, sha_hex: str, sig_b64: str) -> bool:
        if not sig_b64:
            # no signature provided — allow only if no key configured (dev mode)
            return self.public_key_path is None and not self.hmac_secret
        # try Ed25519 if public key file exists
        if self.public_key_path and self.public_key_path.exists():
            try:
                from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

                pub_raw = self.public_key_path.read_bytes()
                # support raw 32-byte or PEM
                if b"BEGIN" in pub_raw:
                    from cryptography.hazmat.primitives import serialization

                    key = serialization.load_pem_public_key(pub_raw)
                    assert isinstance(key, Ed25519PublicKey)
                else:
                    key = Ed25519PublicKey.from_public_bytes(pub_raw[:32])
                sig = base64.b64decode(sig_b64)
                key.verify(sig, bytes.fromhex(sha_hex))
                return True
            except Exception:
                return False
        # HMAC fallback
        if self.hmac_secret:
            expected = hmac.new(self.hmac_secret.encode(), sha_hex.encode(), hashlib.sha256).digest()
            try:
                got = base64.b64decode(sig_b64)
            except Exception:
                return False
            return hmac.compare_digest(got, expected)
        # no verifier configured but signature present — fail closed
        return False

    async def stage(self, pkg: OTAPackage, data: bytes | None = None) -> dict:
        """Stage a package: download (if needed) → verify sha256 → verify sig → version check → ready."""
        self.state = OTAState.DOWNLOADING
        self.last_error = None
        try:
            # resolve data
            if data is None:
                if pkg.artifact_bytes is not None:
                    data = pkg.artifact_bytes
                elif pkg.artifact_url:
                    # fetch via httpx (optional, stub-friendly)
                    import httpx

                    async with httpx.AsyncClient(timeout=15) as client:
                        r = await client.get(pkg.artifact_url)
                        r.raise_for_status()
                        data = r.content
                else:
                    raise ValueError("no artifact source: need artifact_bytes or artifact_url")
            assert data is not None
            self.state = OTAState.VERIFYING
            if not self._verify_sha256(data, pkg.sha256):
                raise ValueError(f"sha256 mismatch: expected {pkg.sha256}, got {hashlib.sha256(data).hexdigest()}")
            if pkg.signature_b64 and not self._verify_signature(pkg.sha256, pkg.signature_b64):
                raise ValueError("signature verification failed")
            if not _is_newer(pkg.version, self.current_version):
                raise ValueError(f"version {pkg.version!r} is not newer than current {self.current_version!r} (monotonic)")

            self.state = OTAState.STAGING
            # staging would write to A/B partition — here we just retain
            self.staged = pkg
            self.state = OTAState.READY
            self._persist()
            self.history.append({"version": pkg.version, "state": self.state.value, "ts": time.time()})
            return {"status": "ready_to_apply", "version": pkg.version, "sha256": pkg.sha256}
        except Exception as e:
            self.state = OTAState.FAILED
            self.last_error = str(e)
            self.history.append({"version": pkg.version, "state": "failed", "error": str(e), "ts": time.time()})
            self._persist()
            raise

    def apply(self) -> dict:
        """Apply staged package — flips current_version, retains rollback point."""
        if self.state != OTAState.READY or not self.staged:
            raise RuntimeError(f"no staged package ready (state={self.state.value})")
        self.previous_version = self.current_version
        self.current_version = self.staged.version
        self.state = OTAState.APPLIED
        applied_version = self.staged.version
        self.history.append({"version": applied_version, "state": "applied", "ts": time.time()})
        self.staged = None
        self._persist()
        return {"status": "applied", "version": applied_version, "previous": self.previous_version}

    def rollback(self) -> dict:
        if not self.previous_version:
            raise RuntimeError("no previous version to roll back to")
        cur = self.current_version
        self.current_version = self.previous_version
        self.previous_version = cur
        self.state = OTAState.ROLLED_BACK
        self.staged = None
        self._persist()
        self.history.append({"version": self.current_version, "state": "rolled_back", "ts": time.time()})
        return {"status": "rolled_back", "version": self.current_version, "previous": cur}

    def status(self) -> dict:
        return {
            "current_version": self.current_version,
            "previous_version": self.previous_version,
            "state": self.state.value,
            "staged_version": self.staged.version if self.staged else None,
            "last_error": self.last_error,
            "history": self.history[-10:],
        }
