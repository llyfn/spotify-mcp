from __future__ import annotations

import pytest
from mcp.server.fastmcp import FastMCP

from spotify_mcp.tools import register_all_tools
from tests._stubs import StubClient, flatten

REMOVED_TOOLS = {
    "follow_artists_or_users",
    "unfollow_artists_or_users",
    "check_following",
    "follow_playlist",
    "unfollow_playlist",
    "get_albums",
    "get_artists",
    "get_tracks",
    "get_shows",
    "get_episodes",
    "get_audiobooks",
    "get_chapters",
}


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
        "get_episode",
        "get_audiobook",
        "get_chapter",
        "get_saved_tracks",
        "whoami",
        "get_followed_artists",
    }
    missing = expected - names
    assert not missing, f"missing tools: {missing}"


async def test_register_all_tools_makes_tools_unique(
    mcp_with_tools: tuple[FastMCP, StubClient],
) -> None:
    mcp, _ = mcp_with_tools
    names = [t.name for t in await mcp.list_tools()]
    assert len(names) == len(set(names))


async def test_tools_backed_by_removed_endpoints_are_not_registered(
    mcp_with_tools: tuple[FastMCP, StubClient],
) -> None:
    mcp, _ = mcp_with_tools
    names = {t.name for t in await mcp.list_tools()}
    assert not (REMOVED_TOOLS & names)


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

    text = flatten(result)
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
    assert "No results found." in flatten(result)


async def test_get_track_tool_formats_response() -> None:
    mcp = FastMCP("test")
    client = StubClient(
        responses={
            ("GET", "/tracks/abc"): {
                "name": "Hello",
                "artists": [{"name": "Adele"}],
                "album": {"name": "25"},
                "duration_ms": 295000,  # 4:55
                "track_number": 1,
                "explicit": False,
                "external_urls": {"spotify": "https://open.spotify.com/track/abc"},
                "popularity": 90,
            }
        }
    )
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    result = await mcp.call_tool("get_track", {"track_id": "abc"})
    text = flatten(result)
    assert "Track: Hello" in text
    assert "Artist(s): Adele" in text
    assert "Album: 25" in text
    assert "Duration: 4:55" in text
    assert "https://open.spotify.com/track/abc" in text
    assert "Popularity" not in text
