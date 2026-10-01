from __future__ import annotations

import os
import re
from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP

from spotify_mcp.client import SpotifyClient


class Live:
    """Calls real tools and resources against the real Spotify API."""

    def __init__(self, mcp: FastMCP, client: SpotifyClient) -> None:
        self._mcp = mcp
        self.client = client

    async def call(self, tool: str, **args: Any) -> str:
        result = await self._mcp.call_tool(tool, args)
        if isinstance(result, tuple):
            result = result[0]
        return "\n".join(getattr(item, "text", "") for item in result)

    async def read(self, uri: str) -> str:
        contents = await self._mcp.read_resource(uri)
        return "\n".join(getattr(c, "content", str(c)) for c in contents)


def require(env_var: str) -> None:
    if os.environ.get(env_var) != "1":
        pytest.skip(f"set {env_var}=1 to run")


def first_id(text: str, section: str | None = None) -> str | None:
    """First `(ID: ...)` in tool output, optionally only after a section heading."""
    if section:
        text = text.split(section, 1)[1] if section in text else ""
    match = re.search(r"\(ID: ([A-Za-z0-9]+)\)", text)
    return match.group(1) if match else None
