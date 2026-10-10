from __future__ import annotations

import secrets

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class BearerTokenMiddleware:
    """Reject HTTP requests that lack ``Authorization: Bearer <token>``."""

    def __init__(self, app: ASGIApp, token: str) -> None:
        if not token:
            raise ValueError("token must not be empty")
        self._app = app
        self._token = token.encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Lifespan events must reach the wrapped app: the streamable-http session
        # manager starts its task group there.
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        scheme, _, supplied = Headers(scope=scope).get("authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not secrets.compare_digest(supplied.encode(), self._token):
            response = JSONResponse(
                {"error": "unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return
        await self._app(scope, receive, send)
