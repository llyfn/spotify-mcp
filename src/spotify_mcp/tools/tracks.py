from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from spotify_mcp.client import SpotifyClient


def register(mcp: FastMCP, client: SpotifyClient) -> None:
    @mcp.tool()
    async def get_track(track_id: str) -> str:
        """Get details of a Spotify track by its ID.

        Args:
            track_id: The Spotify ID of the track.
        """
        data = await client.get(f"/tracks/{track_id}")
        artists = ", ".join(a["name"] for a in data.get("artists", []))
        duration_ms = data.get("duration_ms", 0)
        duration = f"{duration_ms // 60000}:{(duration_ms % 60000) // 1000:02d}"
        album = data.get("album", {})
        lines = [
            f"Track: {data.get('name')}",
            f"Artist(s): {artists}",
            f"Album: {album.get('name', 'N/A')}",
            f"Duration: {duration}",
        ]
        if data.get("popularity") is not None:
            lines.append(f"Popularity: {data['popularity']}")
        lines.append(f"Track Number: {data.get('track_number')}")
        lines.append(f"Explicit: {data.get('explicit', False)}")
        lines.append(f"URL: {data.get('external_urls', {}).get('spotify', 'N/A')}")
        return "\n".join(lines)
