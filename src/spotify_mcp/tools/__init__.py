from __future__ import annotations

from typing import TYPE_CHECKING

from spotify_mcp.tools import (
    albums,
    artists,
    audiobooks,
    follow,
    library,
    player,
    playlists,
    search,
    shows,
    tracks,
    users,
)

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from spotify_mcp.client import SpotifyClient

_MODULES = [
    albums,
    artists,
    tracks,
    search,
    playlists,
    library,
    shows,
    audiobooks,
    users,
    player,
    follow,
]


def register_all_tools(mcp: FastMCP, client: SpotifyClient) -> None:
    """Register all Spotify tool modules with the MCP server."""
    for module in _MODULES:
        module.register(mcp, client)
