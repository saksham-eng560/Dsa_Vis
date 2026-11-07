"""Sliding-window per-client rate limiting as ASGI middleware."""

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Limit POST requests under `/api/` to `per_minute` per client IP."""

    def __init__(self, app: ASGIApp, per_minute: int) -> None:
        super().__init__(app)
        self.per_minute = per_minute
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method != "POST" or not request.url.path.startswith("/api/"):
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self.hits[client]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= self.per_minute:
            retry = int(60 - (now - window[0])) + 1
            return JSONResponse(
                {"detail": "Too many requests — please wait a moment and try again."},
                status_code=429,
                headers={"Retry-After": str(retry)},
            )
        window.append(now)
        return await call_next(request)
