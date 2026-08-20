"""Domain errors — typed for API translation."""
from __future__ import annotations


class GatewayError(Exception):
    status_code: int = 500
    code: str = "gateway_error"


class AuthError(GatewayError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(GatewayError):
    status_code = 403
    code = "forbidden"


class RateLimitedError(GatewayError):
    status_code = 429
    code = "rate_limited"


class BadRequestError(GatewayError):
    status_code = 400
    code = "bad_request"


class DownstreamError(GatewayError):
    status_code = 502
    code = "bad_gateway"

    def __init__(self, message: str, downstream: str = "", status: int = 502):
        super().__init__(message)
        self.downstream = downstream
        self.status_code = 502 if status < 400 else 502
        self.detail = message
