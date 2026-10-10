from __future__ import annotations

from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP
from starlette.testclient import TestClient

from spotify_mcp import server
from spotify_mcp.http_auth import BearerTokenMiddleware

TOKEN = "t" * 43
JSON = {"Content-Type": "application/json"}
AUTH = {"Authorization": f"Bearer {TOKEN}", **JSON}


def test_build_http_app_enables_dns_rebinding_protection() -> None:
    app = FastMCP("test")
    server._build_http_app(app, "sse", None)
    security = app.settings.transport_security
    assert security is not None
    assert security.enable_dns_rebinding_protection is True
    assert security.allowed_hosts == ["127.0.0.1:*", "localhost:*", "[::1]:*"]


def test_build_http_app_wraps_only_when_token_set() -> None:
    assert isinstance(
        server._build_http_app(FastMCP("a"), "streamable-http", TOKEN), BearerTokenMiddleware
    )
    assert not isinstance(
        server._build_http_app(FastMCP("b"), "streamable-http", None), BearerTokenMiddleware
    )


def test_sse_app_rejects_request_without_token() -> None:
    client = TestClient(
        server._build_http_app(FastMCP("t"), "sse", TOKEN), base_url="http://127.0.0.1:8000"
    )
    assert client.post("/messages/", headers=JSON, content=b"{}").status_code == 401


def test_sse_app_passes_authorized_request_to_mcp() -> None:
    client = TestClient(
        server._build_http_app(FastMCP("t"), "sse", TOKEN), base_url="http://127.0.0.1:8000"
    )
    response = client.post("/messages/", headers=AUTH, content=b"{}")
    assert response.status_code == 400
    assert response.text == "session_id is required"


def test_sse_app_rejects_unlisted_host_header() -> None:
    client = TestClient(
        server._build_http_app(FastMCP("t"), "sse", TOKEN), base_url="http://evil.example:8000"
    )
    assert client.post("/messages/", headers=AUTH, content=b"{}").status_code == 421


def test_main_runs_stdio_through_fastmcp(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.delenv("SPOTIFY_MCP_TRANSPORT", raising=False)
    monkeypatch.setattr(server, "_setup", lambda: None)
    monkeypatch.setattr(server.mcp, "run", lambda transport: calls.append(transport))
    monkeypatch.setattr(server.uvicorn, "run", lambda *a, **k: pytest.fail("uvicorn used"))
    server.main()
    assert calls == ["stdio"]


def test_main_runs_http_through_uvicorn(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setenv("SPOTIFY_MCP_TRANSPORT", "streamable-http")
    monkeypatch.delenv("SPOTIFY_MCP_AUTH_TOKEN", raising=False)
    monkeypatch.setattr(server, "_setup", lambda: None)
    monkeypatch.setattr(server, "_build_http_app", lambda *a: "app")
    monkeypatch.setattr(server.uvicorn, "run", lambda app, **kw: captured.update(app=app, **kw))
    server.main()
    assert captured == {"app": "app", "host": "127.0.0.1", "port": 8000, "log_level": "info"}


def test_main_exits_on_invalid_token_before_serving_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPOTIFY_MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("SPOTIFY_MCP_AUTH_TOKEN", "short")
    monkeypatch.setattr(server, "_setup", lambda: pytest.fail("_setup called"))
    monkeypatch.setattr(server.uvicorn, "run", lambda *a, **k: pytest.fail("uvicorn used"))
    with pytest.raises(SystemExit) as exc:
        server.main()
    assert exc.value.code == 1


def test_streamable_http_app_serves_authorized_initialize() -> None:
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "t", "version": "0"},
        },
    }
    headers = {**AUTH, "Accept": "application/json, text/event-stream"}
    with TestClient(
        server._build_http_app(FastMCP("t"), "streamable-http", TOKEN),
        base_url="http://127.0.0.1:8000",
    ) as client:
        assert client.post("/mcp", headers=headers, json=body).status_code == 200
