from __future__ import annotations

from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP
from starlette.testclient import TestClient

from spotify_mcp import server
from spotify_mcp.exceptions import AuthenticationError
from spotify_mcp.http_auth import BearerTokenMiddleware

TOKEN = "t" * 43
JSON = {"Content-Type": "application/json"}
AUTH = {"Authorization": f"Bearer {TOKEN}", **JSON}


def test_build_http_app_enables_dns_rebinding_protection() -> None:
    app = FastMCP("test")
    server._build_http_app(app, "sse", TOKEN)
    security = app.settings.transport_security
    assert security is not None
    assert security.enable_dns_rebinding_protection is True
    assert security.allowed_hosts == ["127.0.0.1:*", "localhost:*", "[::1]:*"]


@pytest.mark.parametrize("transport", ["sse", "streamable-http"])
def test_build_http_app_always_requires_bearer_token(transport: str) -> None:
    assert isinstance(server._build_http_app(FastMCP("a"), transport, TOKEN), BearerTokenMiddleware)


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
    monkeypatch.setattr(server.sys, "argv", ["mcp-server-spotify"])
    calls: list[str] = []
    monkeypatch.delenv("SPOTIFY_MCP_TRANSPORT", raising=False)
    monkeypatch.setattr(server, "_setup", lambda **kw: None)
    monkeypatch.setattr(server.mcp, "run", lambda transport: calls.append(transport))
    monkeypatch.setattr(server.uvicorn, "run", lambda *a, **k: pytest.fail("uvicorn used"))
    server.main()
    assert calls == ["stdio"]


def test_main_runs_http_through_uvicorn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server.sys, "argv", ["mcp-server-spotify"])
    captured: dict[str, Any] = {}
    monkeypatch.setattr(server.mcp.settings, "host", server.mcp.settings.host)
    monkeypatch.setattr(server.mcp.settings, "port", server.mcp.settings.port)
    monkeypatch.setenv("SPOTIFY_MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("SPOTIFY_MCP_AUTH_TOKEN", TOKEN)
    monkeypatch.setattr(server, "_setup", lambda **kw: None)
    monkeypatch.setattr(server, "_build_http_app", lambda *a, **k: "app")
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


def test_sse_app_accepts_configured_allowed_host() -> None:
    app = server._build_http_app(FastMCP("t"), "sse", TOKEN, ["spotify.example.com"])
    client = TestClient(app, base_url="http://spotify.example.com")
    response = client.post("/messages/", headers=AUTH, content=b"{}")
    assert response.status_code == 400
    assert response.text == "session_id is required"


def test_configured_allowed_host_keeps_loopback_hosts() -> None:
    app = FastMCP("t")
    server._build_http_app(app, "sse", TOKEN, ["spotify.example.com"])
    assert app.settings.transport_security is not None
    assert app.settings.transport_security.allowed_hosts == [
        "127.0.0.1:*",
        "localhost:*",
        "[::1]:*",
        "spotify.example.com",
    ]


def test_main_binds_configured_host_and_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server.sys, "argv", ["mcp-server-spotify"])
    captured: dict[str, Any] = {}
    monkeypatch.setattr(server.mcp.settings, "host", server.mcp.settings.host)
    monkeypatch.setattr(server.mcp.settings, "port", server.mcp.settings.port)
    monkeypatch.setenv("SPOTIFY_MCP_TRANSPORT", "sse")
    monkeypatch.setenv("SPOTIFY_MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("SPOTIFY_MCP_PORT", "9123")
    monkeypatch.setenv("SPOTIFY_MCP_AUTH_TOKEN", TOKEN)
    monkeypatch.setenv("SPOTIFY_MCP_ALLOWED_HOSTS", "spotify.example.com")
    monkeypatch.setattr(server, "_setup", lambda **kw: None)
    monkeypatch.setattr(server, "_build_http_app", lambda *a, **k: "app")
    monkeypatch.setattr(server.uvicorn, "run", lambda app, **kw: captured.update(app=app, **kw))
    server.main()
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 9123


def test_main_overrides_preset_fastmcp_host_and_port(monkeypatch: pytest.MonkeyPatch) -> None:
    # Older mcp releases fill these from FASTMCP_HOST / FASTMCP_PORT, bypassing our validation.
    captured: dict[str, Any] = {}
    monkeypatch.setattr(server.mcp.settings, "host", "0.0.0.0")
    monkeypatch.setattr(server.mcp.settings, "port", 9999)
    monkeypatch.setenv("SPOTIFY_MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("SPOTIFY_MCP_AUTH_TOKEN", TOKEN)
    monkeypatch.setattr(server, "_setup", lambda **kw: None)
    monkeypatch.setattr(server, "_build_http_app", lambda *a, **k: "app")
    monkeypatch.setattr(server.uvicorn, "run", lambda app, **kw: captured.update(app=app, **kw))
    server.main()
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 8000


def test_auth_command_runs_browser_flow_without_starting_server(
    spotify_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    async def authenticate(self: server.AuthManager) -> None:
        calls.append("auth")

    monkeypatch.setattr(server.sys, "argv", ["mcp-server-spotify", "auth"])
    monkeypatch.setattr(server.AuthManager, "authenticate", authenticate)
    monkeypatch.setattr(server, "_setup", lambda **kw: pytest.fail("server started"))
    server.main()
    assert calls == ["auth"]


def test_auth_command_exits_on_failure(
    spotify_env: None, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def authenticate(self: server.AuthManager) -> None:
        raise AuthenticationError("Authentication timed out. Please try again.")

    monkeypatch.setattr(server.sys, "argv", ["mcp-server-spotify", "auth"])
    monkeypatch.setattr(server.AuthManager, "authenticate", authenticate)
    with pytest.raises(SystemExit) as exc:
        server.main()
    assert exc.value.code == 1
    assert "Authentication timed out" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("transport", "interactive"), [("stdio", True), ("streamable-http", False), ("sse", False)]
)
def test_only_stdio_allows_interactive_login(
    monkeypatch: pytest.MonkeyPatch, transport: str, interactive: bool
) -> None:
    seen: list[bool] = []
    monkeypatch.setattr(server.mcp.settings, "host", server.mcp.settings.host)
    monkeypatch.setattr(server.mcp.settings, "port", server.mcp.settings.port)
    monkeypatch.setattr(server.sys, "argv", ["mcp-server-spotify"])
    monkeypatch.setenv("SPOTIFY_MCP_TRANSPORT", transport)
    monkeypatch.setenv("SPOTIFY_MCP_AUTH_TOKEN", TOKEN)
    monkeypatch.setattr(server, "_setup", lambda *, interactive_auth: seen.append(interactive_auth))
    monkeypatch.setattr(server.mcp, "run", lambda transport: None)
    monkeypatch.setattr(server, "_build_http_app", lambda *a, **k: "app")
    monkeypatch.setattr(server.uvicorn, "run", lambda *a, **k: None)
    server.main()
    assert seen == [interactive]
