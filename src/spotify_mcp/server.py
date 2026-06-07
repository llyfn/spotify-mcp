from __future__ import annotations

import os
import sys

from mcp.server.fastmcp import FastMCP

from spotify_mcp import prompts, resources
from spotify_mcp.auth import AuthManager
from spotify_mcp.client import SpotifyClient
from spotify_mcp.config import validate_environment
from spotify_mcp.tools import register_all_tools

mcp = FastMCP("spotify")

_VALID_TRANSPORTS = ("stdio", "sse", "streamable-http")


def _setup() -> SpotifyClient:
    validate_environment()
    auth = AuthManager()
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


def main() -> None:
    _setup()
    mcp.run(transport=_resolve_transport())
