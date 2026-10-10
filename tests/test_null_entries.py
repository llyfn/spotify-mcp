from __future__ import annotations

import pytest
from mcp.server.fastmcp import FastMCP

from spotify_mcp.tools import register_all_tools
from tests._stubs import StubClient, flatten


async def test_get_show_marks_null_episodes_unavailable() -> None:
    mcp = FastMCP("test")
    client = StubClient(
        responses={
            ("GET", "/shows/s1"): {
                "name": "Pod",
                "episodes": {"items": [None, {"name": "Ep2", "release_date": "2026-01-02"}]},
            }
        }
    )
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = flatten(await mcp.call_tool("get_show", {"show_id": "s1"}))
    assert "1. (unavailable)" in text
    assert "2. Ep2 (2026-01-02)" in text


async def test_get_show_episodes_marks_null_entries_unavailable() -> None:
    mcp = FastMCP("test")
    client = StubClient(
        responses={
            ("GET", "/shows/s1/episodes"): {
                "total": 2,
                "items": [None, {"id": "e2", "name": "Ep2", "release_date": "2026-01-02"}],
            }
        }
    )
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = flatten(await mcp.call_tool("get_show_episodes", {"show_id": "s1"}))
    assert "showing 1-2 of 2" in text
    assert "1. (unavailable)" in text
    assert "2. Ep2 (2026-01-02, 0min) (ID: e2)" in text


async def test_search_skips_null_items() -> None:
    mcp = FastMCP("test")
    client = StubClient(
        responses={
            ("GET", "/search"): {
                "playlists": {
                    "total": 2,
                    "items": [None, {"id": "p1", "name": "Lofi", "owner": {"display_name": "Bob"}}],
                }
            }
        }
    )
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = flatten(await mcp.call_tool("search", {"query": "lofi", "types": "playlist"}))
    assert "  - Lofi by Bob (ID: p1)" in text


_TRACK = {"id": "t2", "name": "T2", "artists": [{"name": "X"}]}

_NULL_CASES: list[tuple[str, dict, str, dict, list[str]]] = [
    (
        "get_album",
        {"album_id": "al"},
        "/albums/al",
        {"name": "A", "tracks": {"items": [None, {"name": "T2", "duration_ms": 60_000}]}},
        ["1. (unavailable)", "2. T2 (1:00)"],
    ),
    (
        "get_album_tracks",
        {"album_id": "al"},
        "/albums/al/tracks",
        {"total": 2, "items": [None, {**_TRACK, "duration_ms": 60_000}]},
        ["1. (unavailable)", "2. T2 - X (1:00)"],
    ),
    (
        "get_artist_albums",
        {"artist_id": "ar"},
        "/artists/ar/albums",
        {
            "total": 2,
            "items": [
                None,
                {
                    "name": "Alb",
                    "release_date": "2020",
                    "album_type": "album",
                    "artists": [{"name": "X"}],
                },
            ],
        },
        ["showing 1-2 of 2", "- (unavailable)", "- Alb (2020) [album] - X"],
    ),
    (
        "get_audiobook_chapters",
        {"audiobook_id": "ab"},
        "/audiobooks/ab/chapters",
        {"total": 2, "items": [None, {"id": "c2", "name": "Ch2", "duration_ms": 120_000}]},
        ["1. (unavailable)", "2. Ch2 (2min) (ID: c2)"],
    ),
    (
        "get_saved_tracks",
        {},
        "/me/tracks",
        {"total": 2, "items": [{"track": None}, {"track": _TRACK}]},
        ["1. (unavailable)", "2. T2 - X (ID: t2)"],
    ),
    (
        "get_saved_albums",
        {},
        "/me/albums",
        {
            "total": 2,
            "items": [
                {"album": None},
                {
                    "album": {
                        "id": "a2",
                        "name": "A2",
                        "release_date": "2020",
                        "artists": [{"name": "X"}],
                    }
                },
            ],
        },
        ["showing 1-2 of 2", "- (unavailable)", "- A2 by X (2020) (ID: a2)"],
    ),
    (
        "get_saved_shows",
        {},
        "/me/shows",
        {"total": 2, "items": [{"show": None}, {"show": {"id": "s2", "name": "S2"}}]},
        ["showing 1-2 of 2", "- (unavailable)", "- S2 (ID: s2)"],
    ),
    (
        "get_saved_episodes",
        {},
        "/me/episodes",
        {
            "total": 2,
            "items": [
                {"episode": None},
                {"episode": {"id": "e2", "name": "E2", "release_date": "2020"}},
            ],
        },
        ["showing 1-2 of 2", "- (unavailable)", "- E2 (2020) (ID: e2)"],
    ),
    (
        "get_saved_audiobooks",
        {},
        "/me/audiobooks",
        {"total": 2, "items": [None, {"id": "b2", "name": "B2", "authors": [{"name": "X"}]}]},
        ["showing 1-2 of 2", "- (unavailable)", "- B2 by X (ID: b2)"],
    ),
    (
        "get_my_playlists",
        {},
        "/me/playlists",
        {
            "total": 2,
            "items": [
                None,
                {
                    "id": "p2",
                    "name": "P2",
                    "owner": {"display_name": "X"},
                    "items": {"total": 3},
                },
            ],
        },
        ["showing 1-2 of 2", "- (unavailable)", "- P2 (3 tracks, by X) (ID: p2)"],
    ),
    (
        "get_playlist",
        {"playlist_id": "pl"},
        "/playlists/pl",
        {
            "name": "P",
            "owner": {"display_name": "X"},
            "items": {"total": 3, "items": [None, {"item": None}, {"item": _TRACK}]},
        },
        ["1. (unavailable)", "2. (unavailable)", "3. T2 - X"],
    ),
    (
        "get_playlist_items",
        {"playlist_id": "pl"},
        "/playlists/pl/items",
        {"total": 3, "items": [None, {"item": None}, {"item": _TRACK, "added_by": None}]},
        [
            "showing 1-3 of 3",
            "1. (unavailable)",
            "2. (unavailable)",
            "3. T2 - X (added by: unknown)",
        ],
    ),
    (
        "get_followed_artists",
        {},
        "/me/following",
        {"artists": {"total": 2, "items": [None, {"id": "a2", "name": "A2"}]}},
        ["Followed artists (2 of 2):", "- (unavailable)", "- A2 (ID: a2)"],
    ),
    (
        "get_devices",
        {},
        "/me/player/devices",
        {
            "devices": [
                None,
                {"id": "d2", "name": "Phone", "type": "Smartphone", "volume_percent": 50},
            ]
        },
        ["- Phone (Smartphone) - Volume: 50% (ID: d2)"],
    ),
    (
        "get_my_top_items",
        {"item_type": "tracks"},
        "/me/top/tracks",
        {"total": 2, "items": [None, _TRACK]},
        ["1. (unavailable)", "2. T2 - X (ID: t2)"],
    ),
    (
        "get_recently_played",
        {},
        "/me/player/recently-played",
        {"items": [{"track": None, "played_at": "p1"}, {"track": _TRACK, "played_at": "p2"}]},
        ["1. (unavailable)", "2. T2 by X (ID: t2) (played at: p2)"],
    ),
    (
        "get_queue",
        {},
        "/me/player/queue",
        {"currently_playing": None, "queue": [None, _TRACK]},
        ["1. (unavailable)", "2. T2 by X (ID: t2)"],
    ),
]


@pytest.mark.parametrize(
    ("tool", "args", "path", "response", "expected"),
    _NULL_CASES,
    ids=[case[0] for case in _NULL_CASES],
)
async def test_list_tools_tolerate_null_entries(
    tool: str, args: dict, path: str, response: dict, expected: list[str]
) -> None:
    mcp = FastMCP("test")
    client = StubClient(responses={("GET", path): response})
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = flatten(await mcp.call_tool(tool, args))
    for line in expected:
        assert line in text


async def test_resources_tolerate_null_entries() -> None:
    from spotify_mcp import resources as resources_mod

    mcp = FastMCP("test")
    client = StubClient(
        responses={
            ("GET", "/me/top/tracks"): {"items": [None, _TRACK]},
            ("GET", "/me/top/artists"): {"items": [None, {"name": "A2"}]},
            ("GET", "/me/player/queue"): {"queue": [None, _TRACK]},
        }
    )
    resources_mod.register(mcp, client)  # type: ignore[arg-type]
    cases = {
        "spotify://me/top/tracks": ["1. (unavailable)", "2. T2 - X"],
        "spotify://me/top/artists": ["1. (unavailable)", "2. A2"],
        "spotify://me/queue": ["1. (unavailable)", "2. T2 by X (ID: t2)"],
    }
    for uri, expected in cases.items():
        contents = await mcp.read_resource(uri)
        text = "\n".join(getattr(c, "content", str(c)) for c in contents)
        for line in expected:
            assert line in text


async def test_get_devices_reports_none_when_every_entry_is_null() -> None:
    mcp = FastMCP("test")
    client = StubClient(responses={("GET", "/me/player/devices"): {"devices": [None]}})
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = flatten(await mcp.call_tool("get_devices", {}))
    assert text == "No active devices found."


async def test_whoami_tolerates_a_null_device() -> None:
    mcp = FastMCP("test")
    client = StubClient(
        responses={
            ("GET", "/me"): {"display_name": "Alice", "id": "alice"},
            ("GET", "/me/player/devices"): {
                "devices": [None, {"name": "Laptop", "type": "Computer", "is_active": True}]
            },
        }
    )
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = flatten(await mcp.call_tool("whoami", {}))
    assert "Active device: Laptop" in text
