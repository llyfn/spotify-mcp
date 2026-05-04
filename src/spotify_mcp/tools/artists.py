from __future__ import annotations

from typing import TYPE_CHECKING

from spotify_mcp.tools._utils import paged_list

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from spotify_mcp.client import SpotifyClient


def register(mcp: FastMCP, client: SpotifyClient) -> None:
    @mcp.tool()
    async def get_artist(artist_id: str) -> str:
        """Get details of a Spotify artist by their ID.

        Args:
            artist_id: The Spotify ID of the artist.
        """
        data = await client.get(f"/artists/{artist_id}")
        lines = [f"Artist: {data.get('name')}"]
        if data.get("genres"):
            lines.append(f"Genres: {', '.join(data['genres'])}")
        if data.get("followers"):
            lines.append(f"Followers: {data['followers'].get('total', 0):,}")
        if data.get("popularity") is not None:
            lines.append(f"Popularity: {data['popularity']}")
        lines.append(f"URL: {data.get('external_urls', {}).get('spotify', 'N/A')}")
        return "\n".join(lines)

    @mcp.tool()
    async def get_artist_albums(
        artist_id: str,
        include_groups: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> str:
        """Get albums by a Spotify artist.

        Args:
            artist_id: The Spotify ID of the artist.
            include_groups: Comma-separated album types: album, single, appears_on, compilation.
            limit: Maximum number of albums to return (1-50, default 20).
            offset: Index of the first album to return (default 0).
        """
        params: dict = {"limit": limit, "offset": offset}
        if include_groups:
            params["include_groups"] = include_groups
        data = await client.get(f"/artists/{artist_id}/albums", params=params)
        items = data.get("items", [])
        lines = []
        for a in items:
            artists = ", ".join(ar["name"] for ar in a.get("artists", []))
            album_type = a.get("album_type", "")
            release = a.get("release_date", "N/A")
            lines.append(f"- {a['name']} ({release}) [{album_type}] - {artists}")
        total = data.get("total", len(items))
        return paged_list("Albums", lines, total, offset)
