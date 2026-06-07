from __future__ import annotations

from typing import TYPE_CHECKING

from spotify_mcp.tools._utils import paged_list

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from spotify_mcp.client import SpotifyClient


def register(mcp: FastMCP, client: SpotifyClient) -> None:
    @mcp.tool()
    async def get_playlist(playlist_id: str) -> str:
        """Get details of a Spotify playlist.

        Args:
            playlist_id: The Spotify ID of the playlist.
        """
        data = await client.get(f"/playlists/{playlist_id}")
        owner = data.get("owner", {}).get("display_name", "Unknown")
        items_paged = data.get("tracks", {})
        total = items_paged.get("total", 0)
        items = items_paged.get("items", [])
        track_lines = []
        for i, entry in enumerate(items[:20], start=1):
            item = entry.get("track")
            if item:
                artists = ", ".join(a["name"] for a in item.get("artists", []))
                track_lines.append(f"  {i}. {item['name']} - {artists}")
        lines = [
            f"Playlist: {data.get('name')}",
            f"Owner: {owner}",
            f"Description: {data.get('description', 'N/A')}",
            f"Public: {data.get('public')}",
        ]
        followers = data.get("followers")
        if followers and followers.get("total") is not None:
            lines.append(f"Followers: {followers['total']:,}")
        lines.append(f"Total Tracks: {total}")
        lines.append(f"URL: {data.get('external_urls', {}).get('spotify', 'N/A')}")
        result = "\n".join(lines)
        if track_lines:
            shown = min(20, len(items))
            result += f"\n\nTracks (first {shown} of {total}):\n" + "\n".join(track_lines)
        return result

    @mcp.tool()
    async def update_playlist(
        playlist_id: str,
        name: str | None = None,
        description: str | None = None,
        public: bool | None = None,
    ) -> str:
        """Update a playlist's name, description, or visibility.

        Args:
            playlist_id: The Spotify ID of the playlist.
            name: New name for the playlist.
            description: New description for the playlist.
            public: Whether the playlist should be public.
        """
        body: dict = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if public is not None:
            body["public"] = public
        if not body:
            return "No changes specified."
        await client.put(f"/playlists/{playlist_id}", json=body)
        return f"Playlist {playlist_id} updated successfully."

    @mcp.tool()
    async def get_playlist_items(playlist_id: str, limit: int = 20, offset: int = 0) -> str:
        """Get items (tracks/episodes) in a playlist.

        Args:
            playlist_id: The Spotify ID of the playlist.
            limit: Maximum number of items to return (1-100, default 20).
            offset: Index of the first item to return (default 0).
        """
        data = await client.get(
            f"/playlists/{playlist_id}/items",
            params={"limit": limit, "offset": offset},
        )
        items = data.get("items", [])
        lines = []
        for i, entry in enumerate(items, start=offset + 1):
            item = entry.get("track")
            if item:
                artists = ", ".join(a["name"] for a in item.get("artists", []))
                added_by = entry.get("added_by", {}).get("id", "unknown")
                lines.append(f"{i}. {item['name']} - {artists} (added by: {added_by})")
        total = data.get("total", len(items))
        return paged_list("Playlist items", lines, total, offset)

    @mcp.tool()
    async def add_playlist_items(
        playlist_id: str, uris: list[str], position: int | None = None
    ) -> str:
        """Add tracks or episodes to a playlist.

        Args:
            playlist_id: The Spotify ID of the playlist.
            uris: List of Spotify URIs to add (e.g. ["spotify:track:xxx"]).
            position: Position to insert items (0-based). Appends to end if not specified.
        """
        body: dict = {"uris": uris}
        if position is not None:
            body["position"] = position
        await client.post(f"/playlists/{playlist_id}/items", json=body)
        return f"Added {len(uris)} item(s) to playlist {playlist_id}."

    @mcp.tool()
    async def remove_playlist_items(playlist_id: str, uris: list[str]) -> str:
        """Remove tracks or episodes from a playlist.

        Args:
            playlist_id: The Spotify ID of the playlist.
            uris: List of Spotify URIs to remove (e.g. ["spotify:track:xxx"]).
        """
        items = [{"uri": uri} for uri in uris]
        await client.delete(f"/playlists/{playlist_id}/items", json={"items": items})
        return f"Removed {len(uris)} item(s) from playlist {playlist_id}."

    @mcp.tool()
    async def reorder_playlist_items(
        playlist_id: str,
        range_start: int,
        insert_before: int,
        range_length: int = 1,
    ) -> str:
        """Reorder items in a playlist.

        Args:
            playlist_id: The Spotify ID of the playlist.
            range_start: Position of the first item to be reordered.
            insert_before: Position where the items should be inserted.
            range_length: Number of items to reorder (default 1).
        """
        await client.put(
            f"/playlists/{playlist_id}/items",
            json={
                "range_start": range_start,
                "insert_before": insert_before,
                "range_length": range_length,
            },
        )
        return f"Reordered {range_length} item(s) in playlist {playlist_id}."

    @mcp.tool()
    async def get_my_playlists(limit: int = 20, offset: int = 0) -> str:
        """Get the current user's playlists.

        Args:
            limit: Maximum number of playlists to return (1-50, default 20).
            offset: Index of the first playlist to return (default 0).
        """
        data = await client.get("/me/playlists", params={"limit": limit, "offset": offset})
        items = data.get("items", [])
        lines = []
        for p in items:
            owner = p.get("owner", {}).get("display_name", "Unknown")
            count = p.get("tracks", {}).get("total", 0)
            lines.append(f"- {p['name']} ({count} tracks, by {owner}) (ID: {p['id']})")
        total = data.get("total", len(items))
        return paged_list("Your playlists", lines, total, offset)

    @mcp.tool()
    async def create_playlist(
        name: str,
        description: str = "",
        public: bool = True,
    ) -> str:
        """Create a new playlist for the current user.

        Args:
            name: Name for the new playlist.
            description: Description for the playlist.
            public: Whether the playlist should be public (default True).
        """
        body = {
            "name": name,
            "description": description,
            "public": public,
        }
        data = await client.post("/me/playlists", json=body)
        return (
            f"Created playlist: {data.get('name')}\n"
            f"ID: {data.get('id')}\n"
            f"URL: {data.get('external_urls', {}).get('spotify', 'N/A')}"
        )
