from __future__ import annotations

import os

import pytest

from tests.live._helpers import Live, first_id


async def test_catalog_lookups(live: Live) -> None:
    found = await live.call("search", query="Nils Frahm", types="track,album,artist", limit=10)
    track_id = first_id(found, "Tracks (")
    album_id = first_id(found, "Albums (")
    artist_id = first_id(found, "Artists (")
    assert track_id and album_id and artist_id

    assert "Track:" in await live.call("get_track", track_id=track_id)
    assert "Album:" in await live.call("get_album", album_id=album_id)
    assert "Tracks (showing" in await live.call("get_album_tracks", album_id=album_id)
    assert "Artist:" in await live.call("get_artist", artist_id=artist_id)
    assert "Albums (showing" in await live.call("get_artist_albums", artist_id=artist_id)


async def test_shows_and_episodes(live: Live) -> None:
    found = await live.call("search", query="history podcast", types="show,episode")
    show_id = first_id(found, "Shows (")
    episode_id = first_id(found, "Episodes (")
    assert show_id and episode_id

    assert "Show:" in await live.call("get_show", show_id=show_id)
    assert "Episodes (showing" in await live.call("get_show_episodes", show_id=show_id)
    assert "Episode:" in await live.call("get_episode", episode_id=episode_id)


async def test_audiobooks(live: Live) -> None:
    market = os.environ.get("SPOTIFY_LIVE_MARKET", "US")
    found = await live.call("search", query="Sherlock Holmes", types="audiobook", market=market)
    audiobook_id = first_id(found, "Audiobooks (")
    if not audiobook_id:
        pytest.skip(f"no audiobooks available to this account in market {market}")

    assert "Audiobook:" in await live.call(
        "get_audiobook", audiobook_id=audiobook_id, market=market
    )
    chapters = await live.call("get_audiobook_chapters", audiobook_id=audiobook_id, market=market)
    chapter_id = first_id(chapters)
    assert chapter_id
    assert await live.call("get_chapter", chapter_id=chapter_id, market=market)


async def test_playlists(live: Live) -> None:
    own_id = first_id(await live.call("get_my_playlists", limit=5))
    if own_id:
        assert "Playlist:" in await live.call("get_playlist", playlist_id=own_id)
        assert "Playlist items" in await live.call(
            "get_playlist_items", playlist_id=own_id, limit=5
        )

    found = await live.call("search", query="lofi study", types="playlist")
    other_id = first_id(found, "Playlists (")
    assert other_id
    assert "Playlist:" in await live.call("get_playlist", playlist_id=other_id)


@pytest.mark.parametrize(
    "tool",
    [
        "get_saved_tracks",
        "get_saved_albums",
        "get_saved_shows",
        "get_saved_episodes",
        "get_saved_audiobooks",
        "get_followed_artists",
        "get_my_profile",
        "whoami",
        "get_recently_played",
        "get_playback_state",
        "get_currently_playing",
        "get_devices",
        "get_queue",
    ],
)
async def test_tools_without_required_arguments(live: Live, tool: str) -> None:
    assert await live.call(tool)


@pytest.mark.parametrize("item_type", ["tracks", "artists"])
async def test_top_items(live: Live, item_type: str) -> None:
    assert "Top" in await live.call("get_my_top_items", item_type=item_type)


@pytest.mark.parametrize(
    "uri",
    [
        "spotify://me/profile",
        "spotify://me/playback",
        "spotify://me/queue",
        "spotify://me/top/tracks",
        "spotify://me/top/artists",
    ],
)
async def test_resources(live: Live, uri: str) -> None:
    assert await live.read(uri)
