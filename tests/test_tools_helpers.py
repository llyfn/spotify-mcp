from __future__ import annotations

from spotify_mcp.tools._utils import paged_list
from spotify_mcp.tools.player import _format_progress, _format_track


def test_paged_list_first_page() -> None:
    out = paged_list("Tracks", ["a", "b", "c"], total=10, offset=0)
    assert out.startswith("Tracks (showing 1-3 of 10):\n")
    assert out.endswith("a\nb\nc")


def test_paged_list_with_offset() -> None:
    out = paged_list("Albums", ["x", "y"], total=42, offset=20)
    assert out.startswith("Albums (showing 21-22 of 42):\n")


def test_paged_list_empty_lines() -> None:
    out = paged_list("Items", [], total=0, offset=0)
    assert out == "Items (showing 1-0 of 0):\n"


def test_format_track_with_artists_and_album() -> None:
    track = {
        "name": "Song",
        "artists": [{"name": "A"}, {"name": "B"}],
        "album": {"name": "Disc"},
    }
    assert _format_track(track) == "Song by A, B (from Disc)"


def test_format_track_without_album() -> None:
    track = {"name": "Solo", "artists": [{"name": "Only"}]}
    assert _format_track(track) == "Solo by Only"


def test_format_track_without_artists_returns_name_only() -> None:
    track = {"name": "Episode 5", "artists": []}
    assert _format_track(track) == "Episode 5"


def test_format_track_handles_empty_input() -> None:
    assert _format_track({}) == "Nothing playing"
    assert _format_track(None) == "Nothing playing"  # type: ignore[arg-type]


def test_format_progress_normal() -> None:
    # 65s of 185s -> 1:05 / 3:05
    assert _format_progress(65_000, 185_000) == "1:05 / 3:05"


def test_format_progress_pads_seconds() -> None:
    assert _format_progress(5_000, 60_000) == "0:05 / 1:00"


def test_format_progress_handles_none() -> None:
    assert _format_progress(None, 10_000) == "N/A"
    assert _format_progress(10_000, None) == "N/A"
