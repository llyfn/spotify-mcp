from __future__ import annotations

from typing import TYPE_CHECKING

from spotify_mcp.tools._utils import paged_list

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from spotify_mcp.client import SpotifyClient


def register(mcp: FastMCP, client: SpotifyClient) -> None:
    @mcp.tool()
    async def get_album(album_id: str) -> str:
        """Get details of a Spotify album by its ID.

        Args:
            album_id: The Spotify ID of the album.
        """
        data = await client.get(f"/albums/{album_id}")
        tracks = data.get("tracks", {}).get("items", [])
        track_list = "\n".join(
            f"  {i + 1}. {t['name']}"
            f" ({t['duration_ms'] // 60000}:{(t['duration_ms'] % 60000) // 1000:02d})"
            for i, t in enumerate(tracks)
        )
        artists = ", ".join(a["name"] for a in data.get("artists", []))
        lines = [
            f"Album: {data.get('name')}",
            f"Artist(s): {artists}",
            f"Release Date: {data.get('release_date')}",
            f"Total Tracks: {data.get('total_tracks')}",
        ]
        if data.get("popularity") is not None:
            lines.append(f"Popularity: {data['popularity']}")
        lines.append(f"URL: {data.get('external_urls', {}).get('spotify', 'N/A')}")
        lines.append(f"\nTracks:\n{track_list}")
        return "\n".join(lines)

    @mcp.tool()
    async def get_album_tracks(
        album_id: str, limit: int = 20, offset: int = 0
    ) -> str:
        """Get tracks of a Spotify album.

        Args:
            album_id: The Spotify ID of the album.
            limit: Maximum number of tracks to return (1-50, default 20).
            offset: Index of the first track to return (default 0).
        """
        data = await client.get(
            f"/albums/{album_id}/tracks",
            params={"limit": limit, "offset": offset},
        )
        items = data.get("items", [])
        lines = []
        for i, t in enumerate(items, start=offset + 1):
            duration = f"{t['duration_ms'] // 60000}:{(t['duration_ms'] % 60000) // 1000:02d}"
            artists = ", ".join(a["name"] for a in t.get("artists", []))
            lines.append(f"{i}. {t['name']} - {artists} ({duration})")
        total = data.get("total", len(items))
        return paged_list("Tracks", lines, total, offset)
