from __future__ import annotations

from typing import TYPE_CHECKING

from spotify_mcp.tools._utils import format_duration_mmss, paged_list

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from spotify_mcp.client import SpotifyClient


def register(mcp: FastMCP, client: SpotifyClient) -> None:
    @mcp.tool()
    async def get_album(album_id: str, market: str | None = None) -> str:
        """Get details of a Spotify album by its ID.

        Args:
            album_id: The Spotify ID of the album.
            market: ISO 3166-1 alpha-2 country code; affects availability/relinking.
        """
        params = {"market": market} if market else None
        data = await client.get(f"/albums/{album_id}", params=params)
        tracks = data.get("tracks", {}).get("items", [])
        track_list = "\n".join(
            f"  {i + 1}. {t['name']} ({format_duration_mmss(t.get('duration_ms', 0))})"
            if t
            else f"  {i + 1}. (unavailable)"
            for i, t in enumerate(tracks)
        )
        artists = ", ".join(a["name"] for a in data.get("artists", []))
        lines = [
            f"Album: {data.get('name')}",
            f"Artist(s): {artists}",
            f"Release Date: {data.get('release_date')}",
            f"Total Tracks: {data.get('total_tracks')}",
        ]
        lines.append(f"URL: {data.get('external_urls', {}).get('spotify', 'N/A')}")
        lines.append(f"\nTracks:\n{track_list}")
        return "\n".join(lines)

    @mcp.tool()
    async def get_album_tracks(
        album_id: str,
        limit: int = 20,
        offset: int = 0,
        market: str | None = None,
    ) -> str:
        """Get tracks of a Spotify album.

        Args:
            album_id: The Spotify ID of the album.
            limit: Maximum number of tracks to return (1-50, default 20).
            offset: Index of the first track to return (default 0).
            market: ISO 3166-1 alpha-2 country code.
        """
        params: dict = {"limit": limit, "offset": offset}
        if market:
            params["market"] = market
        data = await client.get(f"/albums/{album_id}/tracks", params=params)
        items = data.get("items", [])
        lines = []
        for i, t in enumerate(items, start=offset + 1):
            if not t:
                lines.append(f"{i}. (unavailable)")
                continue
            duration = format_duration_mmss(t.get("duration_ms", 0))
            artists = ", ".join(a["name"] for a in t.get("artists", []))
            lines.append(f"{i}. {t['name']} - {artists} ({duration})")
        total = data.get("total", len(items))
        return paged_list("Tracks", lines, total, offset)
