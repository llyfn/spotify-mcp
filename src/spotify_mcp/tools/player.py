from __future__ import annotations

from typing import TYPE_CHECKING

from spotify_mcp.tools._utils import (
    format_progress,
    format_track,
)

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from spotify_mcp.client import SpotifyClient


# Back-compat aliases; tests import these from this module.
_format_track = format_track
_format_progress = format_progress


# Always request episode-aware payloads so podcast playback renders correctly.
_PLAYER_PARAMS = {"additional_types": "episode"}


def register(mcp: FastMCP, client: SpotifyClient) -> None:
    @mcp.tool()
    async def get_playback_state() -> str:
        """Get the current playback state including track, device, and progress."""
        data = await client.get("/me/player", params=dict(_PLAYER_PARAMS))
        if not data:
            return "No active playback session."
        device = data.get("device", {})
        item = data.get("item", {})
        progress = data.get("progress_ms")
        duration = item.get("duration_ms") if item else None
        return (
            f"Now playing: {format_track(item)}\n"
            f"Progress: {format_progress(progress, duration)}\n"
            f"Device: {device.get('name', 'Unknown')} ({device.get('type', 'Unknown')})\n"
            f"Volume: {device.get('volume_percent', 'N/A')}%\n"
            f"Shuffle: {data.get('shuffle_state', False)}\n"
            f"Repeat: {data.get('repeat_state', 'off')}\n"
            f"Playing: {data.get('is_playing', False)}"
        )

    @mcp.tool()
    async def get_currently_playing() -> str:
        """Get the currently playing track or episode."""
        data = await client.get(
            "/me/player/currently-playing",
            params=dict(_PLAYER_PARAMS),
        )
        if not data or not data.get("item"):
            return "Nothing is currently playing."
        item = data["item"]
        progress = data.get("progress_ms")
        duration = item.get("duration_ms")
        return (
            f"Currently playing: {format_track(item)}\n"
            f"Progress: {format_progress(progress, duration)}\n"
            f"Playing: {data.get('is_playing', False)}"
        )

    @mcp.tool()
    async def play(
        device_id: str | None = None,
        context_uri: str | None = None,
        uris: list[str] | None = None,
        offset_position: int | None = None,
        position_ms: int | None = None,
    ) -> str:
        """Start or resume playback.

        Args:
            device_id: ID of the device to play on. Uses active device if omitted.
            context_uri: Spotify URI of context (album, artist, playlist).
            uris: List of Spotify track URIs to play. E.g. ["spotify:track:xxx"].
            offset_position: Position in the context to start playback (0-based index).
            position_ms: Position in milliseconds to seek to.
        """
        body: dict = {}
        if context_uri:
            body["context_uri"] = context_uri
        if uris:
            body["uris"] = uris
        if offset_position is not None:
            body["offset"] = {"position": offset_position}
        if position_ms is not None:
            body["position_ms"] = position_ms
        params = {"device_id": device_id} if device_id else None
        await client.put("/me/player/play", params=params, json=body or None)
        return "Playback started/resumed."

    @mcp.tool()
    async def pause(device_id: str | None = None) -> str:
        """Pause playback on the active device.

        Args:
            device_id: ID of the device to pause. If not provided, pauses the active device.
        """
        params = {"device_id": device_id} if device_id else None
        await client.put("/me/player/pause", params=params)
        return "Playback paused."

    @mcp.tool()
    async def next_track(device_id: str | None = None) -> str:
        """Skip to the next track.

        Args:
            device_id: ID of the device. If not provided, uses the active device.
        """
        params = {"device_id": device_id} if device_id else None
        await client.post("/me/player/next", params=params)
        return "Skipped to next track."

    @mcp.tool()
    async def previous_track(device_id: str | None = None) -> str:
        """Skip to the previous track.

        Args:
            device_id: ID of the device. If not provided, uses the active device.
        """
        params = {"device_id": device_id} if device_id else None
        await client.post("/me/player/previous", params=params)
        return "Skipped to previous track."

    @mcp.tool()
    async def seek(position_ms: int, device_id: str | None = None) -> str:
        """Seek to a position in the currently playing track.

        Args:
            position_ms: Position in milliseconds to seek to.
            device_id: ID of the device. If not provided, uses the active device.
        """
        params: dict = {"position_ms": position_ms}
        if device_id:
            params["device_id"] = device_id
        await client.put("/me/player/seek", params=params)
        pos_sec = position_ms // 1000
        return f"Seeked to {pos_sec // 60}:{pos_sec % 60:02d}."

    @mcp.tool()
    async def set_repeat(state: str, device_id: str | None = None) -> str:
        """Set the repeat mode for playback.

        Args:
            state: Repeat mode: "track", "context", or "off".
            device_id: ID of the device. If not provided, uses the active device.
        """
        params: dict = {"state": state}
        if device_id:
            params["device_id"] = device_id
        await client.put("/me/player/repeat", params=params)
        return f"Repeat mode set to: {state}."

    @mcp.tool()
    async def set_volume(volume_percent: int, device_id: str | None = None) -> str:
        """Set the playback volume.

        Args:
            volume_percent: Volume level (0-100).
            device_id: ID of the device. If not provided, uses the active device.
        """
        params: dict = {"volume_percent": volume_percent}
        if device_id:
            params["device_id"] = device_id
        await client.put("/me/player/volume", params=params)
        return f"Volume set to {volume_percent}%."

    @mcp.tool()
    async def toggle_shuffle(state: bool | None = None, device_id: str | None = None) -> str:
        """Set or toggle shuffle mode for playback.

        Args:
            state: True to enable, False to disable. If omitted, flips the current state.
            device_id: ID of the device. If not provided, uses the active device.
        """
        if state is None:
            current = await client.get("/me/player", params=dict(_PLAYER_PARAMS))
            current_state = bool(current.get("shuffle_state", False)) if current else False
            state = not current_state
        params: dict = {"state": str(state).lower()}
        if device_id:
            params["device_id"] = device_id
        await client.put("/me/player/shuffle", params=params)
        return f"Shuffle {'enabled' if state else 'disabled'}."

    @mcp.tool()
    async def transfer_playback(device_id: str, play: bool = True) -> str:
        """Transfer playback to a different device.

        Args:
            device_id: ID of the device to transfer to.
            play: Whether to start playing on the new device (default True).
        """
        await client.put("/me/player", json={"device_ids": [device_id], "play": play})
        return f"Playback transferred to device {device_id}."

    @mcp.tool()
    async def get_devices() -> str:
        """Get the user's available Spotify devices."""
        data = await client.get("/me/player/devices")
        devices = data.get("devices", [])
        if not devices:
            return "No active devices found."
        lines = []
        for d in devices:
            active = " (ACTIVE)" if d.get("is_active") else ""
            lines.append(
                f"- {d.get('name')} ({d.get('type', 'Unknown')}) - "
                f"Volume: {d.get('volume_percent', 'N/A')}%{active} (ID: {d.get('id')})"
            )
        return "Available devices:\n" + "\n".join(lines)

    @mcp.tool()
    async def add_to_queue(uri: str, device_id: str | None = None) -> str:
        """Add a track or episode to the playback queue.

        Args:
            uri: Spotify URI of the item to add. E.g. "spotify:track:xxx".
            device_id: ID of the device. If not provided, uses the active device.
        """
        params: dict = {"uri": uri}
        if device_id:
            params["device_id"] = device_id
        await client.post("/me/player/queue", params=params)
        return f"Added {uri} to queue."

    @mcp.tool()
    async def get_queue() -> str:
        """Get the current playback queue."""
        data = await client.get("/me/player/queue", params=dict(_PLAYER_PARAMS))
        currently = data.get("currently_playing")
        queue = data.get("queue", [])
        result = f"Currently playing: {format_track(currently)}\n"
        if queue:
            lines = [f"  {i}. {format_track(t)}" for i, t in enumerate(queue[:20], start=1)]
            result += f"\nUp next ({len(queue)} in queue):\n" + "\n".join(lines)
        else:
            result += "\nQueue is empty."
        return result

    @mcp.tool()
    async def get_recently_played(
        limit: int = 20,
        after: int | None = None,
        before: int | None = None,
    ) -> str:
        """Get the user's recently played tracks.

        Args:
            limit: Maximum number of items to return (1-50, default 20).
            after: Unix-ms cursor; return items played AFTER this timestamp.
            before: Unix-ms cursor; return items played BEFORE this timestamp.
                Only one of `after` / `before` may be set.
        """
        if after is not None and before is not None:
            return "Specify only one of `after` or `before`."
        params: dict = {"limit": limit}
        if after is not None:
            params["after"] = after
        if before is not None:
            params["before"] = before
        data = await client.get("/me/player/recently-played", params=params)
        items = data.get("items", [])
        lines = []
        for i, item in enumerate(items, start=1):
            track = item.get("track", {})
            played_at = item.get("played_at", "N/A")
            lines.append(f"{i}. {format_track(track)} (played at: {played_at})")
        if not lines:
            return "No recently played tracks."
        cursors = data.get("cursors") or {}
        footer = ""
        if cursors.get("before") or cursors.get("after"):
            footer = (
                f"\n\nCursors: before={cursors.get('before', 'N/A')} "
                f"after={cursors.get('after', 'N/A')}"
            )
        return "Recently played:\n" + "\n".join(lines) + footer
