"""Downstream reverse proxy — httpx AsyncClient, header propagation, error mapping."""
from __future__ import annotations

import logging
from typing import Optional, Any

import httpx
from fastapi import Request, Response

from .config import settings
from ..domain.errors import DownstreamError

log = logging.getLogger("gateway.downstream")


class DownstreamClient:
    def __init__(self, timeout_s: Optional[float] = None):
        self.timeout_s = timeout_s or settings.downstream_timeout_s
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(self.timeout_s), follow_redirects=False)
        return self._client

    async def proxy(
        self,
        downstream_base: str,
        downstream_path: str,
        request: Request,
        extra_headers: Optional[dict[str, str]] = None,
        strip_prefix: Optional[str] = None,
    ) -> Response:
        """Forward request to downstream and return FastAPI Response."""
        base = downstream_base.rstrip("/")
        path = downstream_path
        if strip_prefix and path.startswith(strip_prefix):
            path = path[len(strip_prefix):]
            if not path.startswith("/"):
                path = "/" + path
        url = f"{base}{path}"
        if request.url.query:
            url = f"{url}?{request.url.query}"

        # Filter hop-by-hop headers
        hop_by_hop = {"host", "content-length", "connection", "keep-alive", "transfer-encoding", "te", "trailer", "upgrade", "proxy-connection"}
        headers = {k: v for k, v in request.headers.items() if k.lower() not in hop_by_hop}
        if extra_headers:
            headers.update(extra_headers)

        # Preserve authorization for downstream if configured (gateway already verified)
        # Add forwarded headers
        headers["x-forwarded-for"] = request.client.host if request.client else "unknown"
        headers["x-forwarded-proto"] = request.url.scheme
        headers["x-request-id"] = request.headers.get("x-request-id", "")

        body = await request.body()
        method = request.method

        client = await self._get_client()
        try:
            downstream_resp = await client.request(method, url, headers=headers, content=body)
        except httpx.ConnectError as e:
            log.warning("downstream connect error %s -> %s: %s", method, url, e)
            raise DownstreamError(f"Downstream {base} unreachable", downstream=base, status=502) from e
        except httpx.TimeoutException as e:
            log.warning("downstream timeout %s -> %s: %s", method, url, e)
            raise DownstreamError(f"Downstream {base} timeout", downstream=base, status=504) from e
        except Exception as e:
            log.warning("downstream error %s -> %s: %s", method, url, e)
            raise DownstreamError(f"Downstream error: {e}", downstream=base, status=502) from e

        # Build response — strip hop-by-hop from downstream as well
        resp_headers = {k: v for k, v in downstream_resp.headers.items() if k.lower() not in hop_by_hop}
        # Content-type passthrough
        return Response(
            content=downstream_resp.content,
            status_code=downstream_resp.status_code,
            headers=resp_headers,
            media_type=downstream_resp.headers.get("content-type"),
        )

    async def health_check(self, base_url: str, path: str = "/health") -> dict[str, Any]:
        url = f"{base_url.rstrip('/')}{path}"
        client = await self._get_client()
        try:
            r = await client.get(url, timeout=httpx.Timeout(2.0))
            body: Any
            try:
                body = r.json()
            except Exception:
                body = r.text[:500]
            return {"name": base_url, "url": url, "status": "ok" if r.status_code < 400 else "error", "code": r.status_code, "body": body}
        except Exception as e:
            return {"name": base_url, "url": url, "status": "down", "code": 0, "error": str(e)[:300]}

    async def close(self) -> None:
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None


downstream_client = DownstreamClient()
