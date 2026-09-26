"""Focused tests for the new tool behaviors:

- chunking on large playlist/library mutations
- followed-artists cursor
- market parameter threading
- recently_played cursor pagination
- episode-aware player formatting
- whoami diagnostic
"""

from __future__ import annotations

from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP

from spotify_mcp.tools import register_all_tools


class StubClient:
    """Records every call. Optional canned responses keyed by (method, path)."""

    def __init__(self, responses: dict[tuple[str, str], Any] | None = None) -> None:
        self._responses = responses or {}
        self.calls: list[tuple[str, str, dict | None, Any]] = []

    async def _do(self, method: str, path: str, **kwargs: Any) -> Any:
        params = kwargs.get("params")
        json_body = kwargs.get("json")
        self.calls.append((method, path, params, json_body))
        resp = self._responses.get((method, path), {})
        if callable(resp):
            return resp(len([c for c in self.calls if c[0] == method and c[1] == path]) - 1)
        return resp

    async def get(self, path: str, params: dict | None = None) -> Any:
        return await self._do("GET", path, params=params)

    async def post(self, path: str, params: dict | None = None, json: Any = None) -> Any:
        return await self._do("POST", path, params=params, json=json)

    async def put(self, path: str, params: dict | None = None, json: Any = None) -> Any:
        return await self._do("PUT", path, params=params, json=json)

    async def delete(self, path: str, params: dict | None = None, json: Any = None) -> Any:
        return await self._do("DELETE", path, params=params, json=json)


@pytest.fixture
def mcp_setup() -> tuple[FastMCP, StubClient]:
    mcp = FastMCP("test")
    client = StubClient()
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    return mcp, client


def _flatten(result: Any) -> str:
    if isinstance(result, tuple):
        result = result[0]
    parts: list[str] = []
    for item in result:
        text = getattr(item, "text", None)
        if text is not None:
            parts.append(text)
    return "\n".join(parts) if parts else str(result)


# ---------------- chunking ----------------


async def test_add_playlist_items_chunks_at_100(mcp_setup: tuple[FastMCP, StubClient]) -> None:
    mcp, client = mcp_setup
    uris = [f"spotify:track:t{i}" for i in range(250)]
    await mcp.call_tool("add_playlist_items", {"playlist_id": "PL", "uris": uris})

    posts = [c for c in client.calls if c[0] == "POST"]
    assert len(posts) == 3
    assert len(posts[0][3]["uris"]) == 100
    assert len(posts[1][3]["uris"]) == 100
    assert len(posts[2][3]["uris"]) == 50


async def test_add_playlist_items_chunked_with_position(
    mcp_setup: tuple[FastMCP, StubClient],
) -> None:
    mcp, client = mcp_setup
    uris = [f"spotify:track:t{i}" for i in range(150)]
    await mcp.call_tool(
        "add_playlist_items",
        {"playlist_id": "PL", "uris": uris, "position": 10},
    )
    posts = [c for c in client.calls if c[0] == "POST"]
    assert posts[0][3]["position"] == 10
    assert posts[1][3]["position"] == 110


async def test_save_to_library_chunks_at_40(mcp_setup: tuple[FastMCP, StubClient]) -> None:
    mcp, client = mcp_setup
    uris = [f"spotify:track:t{i}" for i in range(100)]
    await mcp.call_tool("save_to_library", {"uris": uris})

    puts = [c for c in client.calls if c[0] == "PUT" and c[1] == "/me/library"]
    assert len(puts) == 3
    assert len(puts[0][2]["uris"].split(",")) == 40
    assert len(puts[2][2]["uris"].split(",")) == 20


async def test_check_saved_in_library_merges_chunked_results() -> None:
    mcp = FastMCP("test")

    def respond(call_idx: int) -> list[bool]:
        return [True] * 40 if call_idx == 0 else [False] * 20

    client = StubClient(responses={("GET", "/me/library/contains"): respond})
    register_all_tools(mcp, client)  # type: ignore[arg-type]

    uris = [f"spotify:track:t{i}" for i in range(60)]
    result = await mcp.call_tool("check_saved_in_library", {"uris": uris})
    text = _flatten(result)
    assert text.count(": saved") == 40
    assert text.count(": not saved") == 20


async def test_remove_from_library_unfollows_playlist_by_uri(
    mcp_setup: tuple[FastMCP, StubClient],
) -> None:
    mcp, client = mcp_setup
    await mcp.call_tool(
        "remove_from_library",
        {"uris": ["spotify:playlist:PL", "spotify:user:alice"]},
    )
    method, path, params, _ = client.calls[0]
    assert (method, path) == ("DELETE", "/me/library")
    assert params == {"uris": "spotify:playlist:PL,spotify:user:alice"}


# ---------------- follow tools ----------------


async def test_get_followed_artists_passes_cursor(mcp_setup: tuple[FastMCP, StubClient]) -> None:
    mcp, client = mcp_setup
    await mcp.call_tool("get_followed_artists", {"limit": 30, "after": "abc"})
    _, _, params, _ = client.calls[0]
    assert params == {"type": "artist", "limit": 30, "after": "abc"}


# ---------------- market threading ----------------


async def test_get_track_threads_market(mcp_setup: tuple[FastMCP, StubClient]) -> None:
    mcp, client = mcp_setup
    await mcp.call_tool("get_track", {"track_id": "abc", "market": "JP"})
    _, path, params, _ = client.calls[0]
    assert path == "/tracks/abc"
    assert params == {"market": "JP"}


async def test_get_album_tracks_threads_market(mcp_setup: tuple[FastMCP, StubClient]) -> None:
    mcp, client = mcp_setup
    await mcp.call_tool("get_album_tracks", {"album_id": "ab", "market": "DE"})
    _, path, params, _ = client.calls[0]
    assert path == "/albums/ab/tracks"
    assert params.get("market") == "DE"


async def test_get_playlist_items_threads_market(
    mcp_setup: tuple[FastMCP, StubClient],
) -> None:
    mcp, client = mcp_setup
    await mcp.call_tool("get_playlist_items", {"playlist_id": "PL", "market": "US"})
    _, path, params, _ = client.calls[0]
    assert path == "/playlists/PL/items"
    assert params.get("market") == "US"


# ---------------- recently_played cursor ----------------


async def test_recently_played_passes_after_cursor(
    mcp_setup: tuple[FastMCP, StubClient],
) -> None:
    mcp, client = mcp_setup
    await mcp.call_tool("get_recently_played", {"limit": 10, "after": 1234567890})
    _, path, params, _ = client.calls[0]
    assert path == "/me/player/recently-played"
    assert params == {"limit": 10, "after": 1234567890}


async def test_recently_played_rejects_both_cursors(
    mcp_setup: tuple[FastMCP, StubClient],
) -> None:
    mcp, client = mcp_setup
    result = await mcp.call_tool("get_recently_played", {"after": 1, "before": 2})
    assert "Specify only one" in _flatten(result)
    assert client.calls == []


# ---------------- player episode-awareness ----------------


async def test_player_state_passes_additional_types() -> None:
    mcp = FastMCP("test")
    client = StubClient(
        responses={
            ("GET", "/me/player"): {
                "device": {"name": "Phone", "type": "Smartphone", "volume_percent": 50},
                "item": {
                    "name": "Ep 1",
                    "show": {"name": "My Podcast"},
                    "id": "ep1",
                    "duration_ms": 600_000,
                },
                "progress_ms": 120_000,
                "is_playing": True,
                "shuffle_state": False,
                "repeat_state": "off",
            }
        }
    )
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    result = await mcp.call_tool("get_playback_state", {})
    _, path, params, _ = client.calls[0]
    assert path == "/me/player"
    assert params == {"additional_types": "episode"}
    text = _flatten(result)
    assert "Ep 1 on My Podcast" in text


async def test_queue_passes_additional_types(mcp_setup: tuple[FastMCP, StubClient]) -> None:
    mcp, client = mcp_setup
    await mcp.call_tool("get_queue", {})
    _, path, params, _ = client.calls[0]
    assert path == "/me/player/queue"
    assert params == {"additional_types": "episode"}


# ---------------- toggle_shuffle auto-flip ----------------


async def test_toggle_shuffle_flips_when_state_omitted() -> None:
    mcp = FastMCP("test")
    client = StubClient(responses={("GET", "/me/player"): {"shuffle_state": True}})
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    await mcp.call_tool("toggle_shuffle", {})
    # First call reads state, second sets shuffle to false (the flip).
    assert client.calls[0][0] == "GET"
    assert client.calls[0][1] == "/me/player"
    set_call = next(c for c in client.calls if c[0] == "PUT")
    assert set_call[1] == "/me/player/shuffle"
    assert set_call[2]["state"] == "false"


# ---------------- profile ----------------

_PROFILE = {
    "display_name": "Alice",
    "id": "alice",
    "account_id": "aB3dE5fG7h",
    "external_urls": {"spotify": "https://open.spotify.com/user/alice"},
}


async def test_get_my_profile_shows_account_id_and_no_removed_fields() -> None:
    mcp = FastMCP("test")
    client = StubClient(responses={("GET", "/me"): _PROFILE})
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = _flatten(await mcp.call_tool("get_my_profile", {}))
    assert "Account ID: aB3dE5fG7h" in text
    for removed in ("Email", "Country", "Product", "Followers"):
        assert removed not in text


async def test_profile_resource_shows_account_id() -> None:
    from spotify_mcp import resources as resources_mod

    mcp = FastMCP("test")
    client = StubClient(responses={("GET", "/me"): _PROFILE})
    resources_mod.register(mcp, client)  # type: ignore[arg-type]
    contents = await mcp.read_resource("spotify://me/profile")
    text = "\n".join(getattr(c, "content", str(c)) for c in contents)
    assert "Account ID: aB3dE5fG7h" in text
    assert "Plan" not in text


# ---------------- whoami ----------------


async def test_whoami_includes_profile_and_scopes() -> None:
    mcp = FastMCP("test")
    client = StubClient(
        responses={
            ("GET", "/me"): {"display_name": "Alice", "id": "alice", "account_id": "aB3"},
            ("GET", "/me/player/devices"): {
                "devices": [
                    {"name": "Laptop", "type": "Computer", "is_active": True, "volume_percent": 70},
                ]
            },
        }
    )
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    result = await mcp.call_tool("whoami", {})
    text = _flatten(result)
    assert "Alice" in text
    assert "Active device: Laptop" in text
    assert "user-read-private" in text
    assert "Account ID: aB3" in text
    assert "Country" not in text


# ---------------- playlist fields ----------------


async def test_get_playlist_reads_items_not_deprecated_tracks() -> None:
    mcp = FastMCP("test")
    client = StubClient(
        responses={
            ("GET", "/playlists/PL"): {
                "name": "Mine",
                "owner": {"display_name": "Alice"},
                "public": True,
                "items": {
                    "total": 1,
                    "items": [{"item": {"name": "Song", "artists": [{"name": "A"}]}}],
                },
            }
        }
    )
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = _flatten(await mcp.call_tool("get_playlist", {"playlist_id": "PL"}))
    assert "Total Tracks: 1" in text
    assert "1. Song - A" in text
    assert "Followers" not in text


async def test_get_playlist_without_items_says_items_unavailable() -> None:
    mcp = FastMCP("test")
    client = StubClient(
        responses={("GET", "/playlists/PL"): {"name": "Theirs", "owner": {"display_name": "Bob"}}}
    )
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = _flatten(await mcp.call_tool("get_playlist", {"playlist_id": "PL"}))
    assert "Items: not available" in text
    assert "Total Tracks" not in text


async def test_get_playlist_items_reads_item_not_deprecated_track() -> None:
    mcp = FastMCP("test")
    client = StubClient(
        responses={
            ("GET", "/playlists/PL/items"): {
                "total": 1,
                "items": [
                    {"item": {"name": "Song", "artists": [{"name": "A"}]}, "added_by": {"id": "u"}}
                ],
            }
        }
    )
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = _flatten(await mcp.call_tool("get_playlist_items", {"playlist_id": "PL"}))
    assert "1. Song - A (added by: u)" in text


async def test_get_my_playlists_counts_from_items_ref() -> None:
    mcp = FastMCP("test")
    client = StubClient(
        responses={
            ("GET", "/me/playlists"): {
                "total": 1,
                "items": [
                    {
                        "id": "PL",
                        "name": "Mine",
                        "owner": {"display_name": "A"},
                        "items": {"total": 7},
                    }
                ],
            }
        }
    )
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = _flatten(await mcp.call_tool("get_my_playlists", {}))
    assert "(7 tracks, by A)" in text


# ---------------- removed fields ----------------


async def test_search_artists_does_not_show_follower_count() -> None:
    mcp = FastMCP("test")
    client = StubClient(
        responses={
            ("GET", "/search"): {
                "artists": {"total": 1, "items": [{"id": "a1", "name": "Radiohead"}]}
            }
        }
    )
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = _flatten(await mcp.call_tool("search", {"query": "x", "types": "artist"}))
    assert "Radiohead (ID: a1)" in text
    assert "followers" not in text


async def test_get_episode_does_not_show_publisher_placeholder() -> None:
    mcp = FastMCP("test")
    client = StubClient(
        responses={("GET", "/episodes/e1"): {"name": "Ep", "show": {"name": "Pod"}}}
    )
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = _flatten(await mcp.call_tool("get_episode", {"episode_id": "e1"}))
    assert "Show: Pod" in text
    assert "Unknown" not in text


async def test_get_audiobook_does_not_show_publisher() -> None:
    mcp = FastMCP("test")
    client = StubClient(responses={("GET", "/audiobooks/b1"): {"name": "Book"}})
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = _flatten(await mcp.call_tool("get_audiobook", {"audiobook_id": "b1"}))
    assert "Publisher" not in text


async def test_get_saved_shows_does_not_show_publisher_placeholder() -> None:
    mcp = FastMCP("test")
    client = StubClient(
        responses={
            ("GET", "/me/shows"): {"total": 1, "items": [{"show": {"id": "s1", "name": "Pod"}}]}
        }
    )
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = _flatten(await mcp.call_tool("get_saved_shows", {}))
    assert "- Pod (ID: s1)" in text


# ---------------- resources / prompts registration ----------------


async def test_resources_and_prompts_register_without_error() -> None:
    from spotify_mcp import prompts as prompts_mod
    from spotify_mcp import resources as resources_mod

    mcp = FastMCP("test")
    client = StubClient()
    resources_mod.register(mcp, client)  # type: ignore[arg-type]
    prompts_mod.register(mcp)

    resource_uris = {str(r.uri) for r in await mcp.list_resources()}
    assert "spotify://me/profile" in resource_uris
    assert "spotify://me/playback" in resource_uris

    prompt_names = {p.name for p in await mcp.list_prompts()}
    assert {
        "build_playlist_from_recent",
        "weekly_listening_summary",
        "playlist_from_artists",
        "library_cleanup",
    } <= prompt_names
