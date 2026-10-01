from __future__ import annotations

import re

import pytest

from tests.live._helpers import Live, first_id, require

_SEARCHES = {
    "track": ("Nils Frahm Says", "Tracks ("),
    "artist": ("Nils Frahm", "Artists ("),
    "playlist": ("lofi study", "Playlists ("),
}


@pytest.mark.parametrize("kind", ["track", "artist", "playlist"])
async def test_library_round_trip(live: Live, kind: str) -> None:
    require("SPOTIFY_LIVE_WRITE")
    query, section = _SEARCHES[kind]
    item_id = first_id(await live.call("search", query=query, types=kind), section)
    assert item_id
    uri = f"spotify:{kind}:{item_id}"
    if ": saved" in await live.call("check_saved_in_library", uris=[uri]):
        pytest.skip(f"{uri} is already in the library; leaving it untouched")

    await live.call("save_to_library", uris=[uri])
    try:
        assert ": saved" in await live.call("check_saved_in_library", uris=[uri])
    finally:
        await live.call("remove_from_library", uris=[uri])
    assert ": not saved" in await live.call("check_saved_in_library", uris=[uri])


async def test_playlist_lifecycle(live: Live) -> None:
    require("SPOTIFY_LIVE_WRITE")
    found = await live.call("search", query="Nils Frahm", types="track", limit=3)
    track_ids = re.findall(r"\(ID: ([A-Za-z0-9]+)\)", found)[:2]
    assert len(track_ids) == 2
    uris = [f"spotify:track:{track_id}" for track_id in track_ids]

    created = await live.call("create_playlist", name="spotify-mcp live test", public=False)
    match = re.search(r"^ID: (\S+)$", created, re.MULTILINE)
    assert match
    playlist_id = match.group(1)
    try:
        await live.call("update_playlist", playlist_id=playlist_id, description="temporary")
        await live.call("add_playlist_items", playlist_id=playlist_id, uris=uris)
        assert "of 2)" in await live.call("get_playlist_items", playlist_id=playlist_id)
        await live.call(
            "reorder_playlist_items", playlist_id=playlist_id, range_start=0, insert_before=2
        )
        await live.call("remove_playlist_items", playlist_id=playlist_id, uris=uris[:1])
        assert "of 1)" in await live.call("get_playlist_items", playlist_id=playlist_id)
    finally:
        await live.call("remove_from_library", uris=[f"spotify:playlist:{playlist_id}"])
