"""
limits.py - request size limit and per-IP rate limit.
"""
import time
from collections import defaultdict, deque

from fastapi import Request

from errors import ApiError, error_response


class BodySizeLimitMiddleware:
    """Rejects oversized request bodies with 413 BEFORE they are parsed.

    Checks Content-Length up front, and also counts bytes as they arrive, so a client
    that leaves out Content-Length (chunked upload) can't get round the limit."""

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        headers = dict(scope.get("headers") or [])
        length = headers.get(b"content-length")
        if length is not None:
            try:
                declared = int(length)
            except ValueError:
                return await error_response(400, "bad_request", "Invalid Content-Length header.")(scope, receive, send)
            if declared > self.max_bytes:
                return await self._too_large()(scope, receive, send)

        received = 0
        max_bytes = self.max_bytes

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > max_bytes:
                    raise ApiError(413, "payload_too_large", f"Request body exceeds {max_bytes:,} bytes.")
            return message

        await self.app(scope, limited_receive, send)

    def _too_large(self):
        return error_response(413, "payload_too_large", f"Request body exceeds {self.max_bytes:,} bytes.")


class RateLimiter:
    """Sliding one-minute window per client IP. Use as a FastAPI dependency.
    Runs on the event loop (async), so no locking is needed."""

    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self.hits: dict[str, deque] = defaultdict(deque)

    async def __call__(self, request: Request):
        if self.per_minute <= 0:
            return
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self.hits[ip]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= self.per_minute:
            retry_after = int(60 - (now - window[0])) + 1
            raise ApiError(
                429, "rate_limited",
                "Too many checks in a short time. Please wait a moment and try again.",
                headers={"Retry-After": str(retry_after)},
            )
        window.append(now)
        if len(self.hits) > 10_000:   # stop the table itself growing without bound
            for key in [k for k, v in self.hits.items() if not v]:
                del self.hits[key]