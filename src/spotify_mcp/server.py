from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from spotify_mcp.auth import AuthManager
from spotify_mcp.client import SpotifyClient
from spotify_mcp.config import validate_environment
from spotify_mcp.tools import register_all_tools

mcp = FastMCP("spotify")


def _setup() -> None:
    validate_environment()
    auth = AuthManager()
    client = SpotifyClient(auth)
    register_all_tools(mcp, client)


def main() -> None:
    _setup()
    mcp.run(transport="stdio")
