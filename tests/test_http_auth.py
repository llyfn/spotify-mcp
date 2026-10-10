from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from spotify_mcp.http_auth import BearerTokenMiddleware

TOKEN = "t" * 43


async def _ok(_: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def _client() -> TestClient:
    inner = Starlette(routes=[Route("/", _ok)])
    return TestClient(BearerTokenMiddleware(inner, TOKEN))


def test_missing_header_is_rejected() -> None:
    response = _client().get("/")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"error": "unauthorized"}


def test_wrong_token_is_rejected() -> None:
    response = _client().get("/", headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401


def test_non_bearer_scheme_is_rejected() -> None:
    response = _client().get("/", headers={"Authorization": f"Basic {TOKEN}"})
    assert response.status_code == 401


def test_correct_token_reaches_wrapped_app() -> None:
    response = _client().get("/", headers={"Authorization": f"Bearer {TOKEN}"})
    assert response.status_code == 200
    assert response.text == "ok"


def test_lowercase_scheme_is_accepted() -> None:
    response = _client().get("/", headers={"Authorization": f"bearer {TOKEN}"})
    assert response.status_code == 200


def test_lifespan_reaches_wrapped_app() -> None:
    started: list[bool] = []

    @asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncIterator[None]:
        started.append(True)
        yield

    inner = Starlette(routes=[Route("/", _ok)], lifespan=lifespan)
    with TestClient(BearerTokenMiddleware(inner, TOKEN)):
        pass
    assert started == [True]


def test_empty_token_is_rejected_at_construction() -> None:
    inner = Starlette(routes=[Route("/", _ok)])
    with pytest.raises(ValueError):
        BearerTokenMiddleware(inner, "")


async def _run_websocket(headers: list[tuple[bytes, bytes]]) -> tuple[list[str], list[dict]]:
    reached: list[str] = []
    sent: list[dict] = []

    async def inner(scope: dict, receive: object, send: object) -> None:
        reached.append(scope["type"])

    async def receive() -> dict:
        return {"type": "websocket.connect"}

    async def send(message: dict) -> None:
        sent.append(message)

    scope = {"type": "websocket", "path": "/", "headers": headers}
    await BearerTokenMiddleware(inner, TOKEN)(scope, receive, send)
    return reached, sent


def test_websocket_without_token_is_closed_before_reaching_app() -> None:
    reached, sent = asyncio.run(_run_websocket([]))
    assert reached == []
    assert sent == [{"type": "websocket.close", "code": 1008}]


def test_websocket_with_correct_token_reaches_wrapped_app() -> None:
    headers = [(b"authorization", f"Bearer {TOKEN}".encode())]
    reached, sent = asyncio.run(_run_websocket(headers))
    assert reached == ["websocket"]
    assert sent == []
