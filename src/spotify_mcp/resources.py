from __future__ import annotations

from typing import TYPE_CHECKING

from spotify_mcp.exceptions import SpotifyAPIError
from spotify_mcp.tools._utils import format_progress, format_track

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from spotify_mcp.client import SpotifyClient


def register(mcp: FastMCP, client: SpotifyClient) -> None:
    """Expose user state as MCP resources.

    Resources are read-only snapshots a client can subscribe to or include
    as context. All paths live under the `spotify://` URI scheme.
    """

    @mcp.resource("spotify://me/profile", mime_type="text/plain")
    async def me_profile() -> str:
        data = await client.get("/me")
        return (
            f"User: {data.get('display_name', 'N/A')}\n"
            f"ID: {data.get('id')}\n"
            f"Country: {data.get('country', 'N/A')}\n"
            f"Plan: {data.get('product', 'N/A')}\n"
            f"Followers: {data.get('followers', {}).get('total', 0):,}"
        )

    @mcp.resource("spotify://me/playback", mime_type="text/plain")
    async def me_playback() -> str:
        try:
            data = await client.get("/me/player", params={"additional_types": "episode"})
        except SpotifyAPIError as e:
            return f"Playback unavailable: {e.message}"
        if not data:
            return "No active playback session."
        item = data.get("item") or {}
        return (
            f"Now playing: {format_track(item)}\n"
            f"Progress: {format_progress(data.get('progress_ms'), item.get('duration_ms'))}\n"
            f"Playing: {data.get('is_playing', False)}\n"
            f"Shuffle: {data.get('shuffle_state', False)} / "
            f"Repeat: {data.get('repeat_state', 'off')}"
        )

    @mcp.resource("spotify://me/queue", mime_type="text/plain")
    async def me_queue() -> str:
        try:
            data = await client.get("/me/player/queue", params={"additional_types": "episode"})
        except SpotifyAPIError as e:
            return f"Queue unavailable: {e.message}"
        currently = data.get("currently_playing")
        queue = data.get("queue", []) or []
        result = f"Currently playing: {format_track(currently)}\n"
        if queue:
            lines = [f"  {i}. {format_track(t)}" for i, t in enumerate(queue[:20], start=1)]
            result += f"\nUp next ({len(queue)}):\n" + "\n".join(lines)
        else:
            result += "\nQueue is empty."
        return result

    @mcp.resource("spotify://me/top/tracks", mime_type="text/plain")
    async def me_top_tracks() -> str:
        data = await client.get(
            "/me/top/tracks",
            params={"time_range": "medium_term", "limit": 20, "offset": 0},
        )
        items = data.get("items", []) or []
        if not items:
            return "No top tracks."
        lines = []
        for i, t in enumerate(items, start=1):
            artists = ", ".join(a["name"] for a in t.get("artists", []))
            lines.append(f"{i}. {t.get('name')} - {artists}")
        return "Top tracks (last ~6 months):\n" + "\n".join(lines)

    @mcp.resource("spotify://me/top/artists", mime_type="text/plain")
    async def me_top_artists() -> str:
        data = await client.get(
            "/me/top/artists",
            params={"time_range": "medium_term", "limit": 20, "offset": 0},
        )
        items = data.get("items", []) or []
        if not items:
            return "No top artists."
        lines = []
        for i, a in enumerate(items, start=1):
            genres = ", ".join(a.get("genres", [])[:3]) or "N/A"
            lines.append(f"{i}. {a.get('name')} ({genres})")
        return "Top artists (last ~6 months):\n" + "\n".join(lines)
