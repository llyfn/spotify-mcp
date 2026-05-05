from __future__ import annotations

from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP

from spotify_mcp.tools import register_all_tools


class StubClient:
    """Records calls instead of hitting the network."""

    def __init__(self, responses: dict[tuple[str, str], Any] | None = None) -> None:
        self._responses = responses or {}
        self.calls: list[tuple[str, str, dict | None, Any]] = []

    async def _do(self, method: str, path: str, **kwargs: Any) -> Any:
        params = kwargs.get("params")
        json_body = kwargs.get("json")
        self.calls.append((method, path, params, json_body))
        return self._responses.get((method, path), {})

    async def get(self, path: str, params: dict | None = None) -> Any:
        return await self._do("GET", path, params=params)

    async def post(self, path: str, params: dict | None = None, json: Any = None) -> Any:
        return await self._do("POST", path, params=params, json=json)

    async def put(self, path: str, params: dict | None = None, json: Any = None) -> Any:
        return await self._do("PUT", path, params=params, json=json)

    async def delete(self, path: str, params: dict | None = None, json: Any = None) -> Any:
        return await self._do("DELETE", path, params=params, json=json)


@pytest.fixture
def mcp_with_tools() -> tuple[FastMCP, StubClient]:
    mcp = FastMCP("test")
    client = StubClient()
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    return mcp, client


async def test_register_all_tools_registers_expected_tools(
    mcp_with_tools: tuple[FastMCP, StubClient],
) -> None:
    mcp, _ = mcp_with_tools
    names = {t.name for t in await mcp.list_tools()}
    # Spot-check one tool from each module so a missing module fails the test.
    expected = {
        "search",
        "get_track",
        "get_album",
        "get_artist",
        "get_playlist",
        "get_my_profile",
        "get_playback_state",
        "get_show",
        "get_audiobook",
        "get_saved_tracks",
    }
    missing = expected - names
    assert not missing, f"missing tools: {missing}"


async def test_register_all_tools_makes_tools_unique(
    mcp_with_tools: tuple[FastMCP, StubClient],
) -> None:
    mcp, _ = mcp_with_tools
    names = [t.name for t in await mcp.list_tools()]
    assert len(names) == len(set(names))


async def test_search_tool_calls_correct_endpoint() -> None:
    mcp = FastMCP("test")
    client = StubClient(
        responses={
            (
                "GET",
                "/search",
            ): {
                "tracks": {
                    "total": 1,
                    "items": [
                        {
                            "id": "t1",
                            "name": "Song",
                            "artists": [{"name": "Artist"}],
                        }
                    ],
                }
            }
        }
    )
    register_all_tools(mcp, client)  # type: ignore[arg-type]

    result = await mcp.call_tool("search", {"query": "love", "types": "track", "limit": 5})
    method, path, params, _ = client.calls[0]
    assert method == "GET"
    assert path == "/search"
    assert params == {"q": "love", "type": "track", "limit": 5, "offset": 0}

    text = _flatten(result)
    assert "Song" in text
    assert "Artist" in text
    assert "t1" in text


async def test_search_tool_passes_market() -> None:
    mcp = FastMCP("test")
    client = StubClient()
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    await mcp.call_tool(
        "search",
        {"query": "x", "market": "US"},
    )
    _, _, params, _ = client.calls[0]
    assert params is not None and params.get("market") == "US"


async def test_search_tool_no_results() -> None:
    mcp = FastMCP("test")
    client = StubClient(responses={("GET", "/search"): {"tracks": {"total": 0, "items": []}}})
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    result = await mcp.call_tool("search", {"query": "zzz"})
    assert "No results found." in _flatten(result)


async def test_get_track_tool_formats_response() -> None:
    mcp = FastMCP("test")
    client = StubClient(
        responses={
            ("GET", "/tracks/abc"): {
                "name": "Hello",
                "artists": [{"name": "Adele"}],
                "album": {"name": "25"},
                "duration_ms": 295000,  # 4:55
                "popularity": 90,
                "track_number": 1,
                "explicit": False,
                "external_urls": {"spotify": "https://open.spotify.com/track/abc"},
            }
        }
    )
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    result = await mcp.call_tool("get_track", {"track_id": "abc"})
    text = _flatten(result)
    assert "Track: Hello" in text
    assert "Artist(s): Adele" in text
    assert "Album: 25" in text
    assert "Duration: 4:55" in text
    assert "Popularity: 90" in text
    assert "https://open.spotify.com/track/abc" in text


def _flatten(call_tool_result: Any) -> str:
    """call_tool returns a list[ContentBlock] or (list, dict) tuple depending on version.

    We only need a string for substring assertions, so coerce defensively.
    """
    if isinstance(call_tool_result, tuple):
        call_tool_result = call_tool_result[0]
    parts: list[str] = []
    for item in call_tool_result:
        text = getattr(item, "text", None)
        if text is not None:
            parts.append(text)
    return "\n".join(parts) if parts else str(call_tool_result)
