from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import Sequence

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.types import ASGIApp

from spotify_mcp import prompts, resources
from spotify_mcp.auth import AuthManager
from spotify_mcp.client import SpotifyClient
from spotify_mcp.config import (
    get_mcp_allowed_hosts,
    get_mcp_host,
    get_mcp_port,
    validate_environment,
    validate_http_environment,
)
from spotify_mcp.exceptions import AuthenticationError
from spotify_mcp.http_auth import BearerTokenMiddleware
from spotify_mcp.tools import register_all_tools

mcp = FastMCP("spotify")

_VALID_TRANSPORTS = ("stdio", "sse", "streamable-http")
_LOOPBACK_ALLOWED_HOSTS = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
_LOOPBACK_ALLOWED_ORIGINS = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]


def _setup(*, interactive_auth: bool) -> SpotifyClient:
    validate_environment()
    auth = AuthManager(interactive=interactive_auth)
    client = SpotifyClient(auth)
    register_all_tools(mcp, client)
    resources.register(mcp, client)
    prompts.register(mcp)
    return client


def _resolve_transport() -> str:
    raw = os.environ.get("SPOTIFY_MCP_TRANSPORT", "stdio").lower()
    if raw not in _VALID_TRANSPORTS:
        print(
            f"Unknown SPOTIFY_MCP_TRANSPORT={raw!r}. "
            f"Expected one of: {', '.join(_VALID_TRANSPORTS)}. Using stdio.",
            file=sys.stderr,
        )
        return "stdio"
    return raw


def _build_http_app(
    server: FastMCP,
    transport: str,
    auth_token: str,
    allowed_hosts: Sequence[str] = (),
) -> ASGIApp:
    # Set explicitly: older mcp releases default to no DNS-rebinding protection.
    server.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[*_LOOPBACK_ALLOWED_HOSTS, *allowed_hosts],
        allowed_origins=list(_LOOPBACK_ALLOWED_ORIGINS),
    )
    app = server.streamable_http_app() if transport == "streamable-http" else server.sse_app()
    return BearerTokenMiddleware(app, auth_token)


def _run_auth_command() -> None:
    validate_environment()
    try:
        asyncio.run(AuthManager().authenticate())
    except AuthenticationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    if sys.argv[1:] == ["auth"]:
        _run_auth_command()
        return
    transport = _resolve_transport()
    auth_token = None if transport == "stdio" else validate_http_environment()
    # An HTTP server has no terminal or browser to finish a login inside a tool call.
    _setup(interactive_auth=transport == "stdio")
    if auth_token is None:
        mcp.run(transport="stdio")
        return
    mcp.settings.host = get_mcp_host()
    mcp.settings.port = get_mcp_port()
    app = _build_http_app(mcp, transport, auth_token, get_mcp_allowed_hosts())
    uvicorn.run(
        app,
        host=mcp.settings.host,
        port=mcp.settings.port,
        log_level=mcp.settings.log_level.lower(),
    )
