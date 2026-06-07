from __future__ import annotations

from typing import TYPE_CHECKING

from spotify_mcp.tools._utils import format_duration_mmss

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from spotify_mcp.client import SpotifyClient


_TRACKS_MAX_IDS = 50


def register(mcp: FastMCP, client: SpotifyClient) -> None:
    @mcp.tool()
    async def get_track(track_id: str, market: str | None = None) -> str:
        """Get details of a Spotify track by its ID.

        Args:
            track_id: The Spotify ID of the track.
            market: ISO 3166-1 alpha-2 country code; affects availability/relinking.
        """
        params = {"market": market} if market else None
        data = await client.get(f"/tracks/{track_id}", params=params)
        artists = ", ".join(a["name"] for a in data.get("artists", []))
        duration = format_duration_mmss(data.get("duration_ms", 0))
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

    @mcp.tool()
    async def get_tracks(track_ids: list[str], market: str | None = None) -> str:
        """Get details of multiple tracks in one call (up to 50 IDs).

        Args:
            track_ids: List of Spotify track IDs (max 50).
            market: ISO 3166-1 alpha-2 country code.
        """
        if not track_ids:
            return "No track IDs provided."
        if len(track_ids) > _TRACKS_MAX_IDS:
            return f"Too many IDs: {len(track_ids)}. Max is {_TRACKS_MAX_IDS}."
        params: dict = {"ids": ",".join(track_ids)}
        if market:
            params["market"] = market
        data = await client.get("/tracks", params=params)
        tracks = data.get("tracks", [])
        lines = []
        for t in tracks:
            if not t:
                lines.append("- (not found)")
                continue
            artists = ", ".join(a["name"] for a in t.get("artists", []))
            duration = format_duration_mmss(t.get("duration_ms", 0))
            lines.append(f"- {t.get('name')} by {artists} ({duration}) (ID: {t.get('id')})")
        return f"Tracks ({len(lines)}):\n" + "\n".join(lines)
