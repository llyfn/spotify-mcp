from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from mcp.server.fastmcp import FastMCP

from spotify_mcp import resources as resources_mod
from spotify_mcp.auth import AuthManager
from spotify_mcp.client import SpotifyClient
from spotify_mcp.tools import register_all_tools
from tests.live._helpers import Live

LIVE_DIR = Path(__file__).parent


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("SPOTIFY_LIVE_TESTS") == "1":
        return
    skip = pytest.mark.skip(reason="set SPOTIFY_LIVE_TESTS=1 to run against the real Spotify API")
    for item in items:
        if LIVE_DIR in item.path.parents:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def _isolate_credentials() -> None:
    """Overrides the root fixture: live tests use the real ~/.spotify-mcp token."""


@pytest.fixture
async def live() -> AsyncIterator[Live]:
    client = SpotifyClient(AuthManager())
    mcp = FastMCP("live")
    register_all_tools(mcp, client)
    resources_mod.register(mcp, client)
    yield Live(mcp, client)
    await client.aclose()
