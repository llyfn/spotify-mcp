from __future__ import annotations

from typing import TYPE_CHECKING

from spotify_mcp.tools._utils import chunked

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from spotify_mcp.client import SpotifyClient


_FOLLOWING_MAX_PER_REQUEST = 50
_VALID_FOLLOW_TYPES = ("artist", "user")


def _validate_type(follow_type: str) -> str | None:
    if follow_type not in _VALID_FOLLOW_TYPES:
        return f"Invalid type '{follow_type}'. Must be one of: {', '.join(_VALID_FOLLOW_TYPES)}."
    return None


def register(mcp: FastMCP, client: SpotifyClient) -> None:
    @mcp.tool()
    async def get_followed_artists(limit: int = 20, after: str | None = None) -> str:
        """Get the current user's followed artists. Cursor-paginated.

        Args:
            limit: Maximum number of artists to return (1-50, default 20).
            after: Cursor (last artist ID from previous page) to fetch the next page.
        """
        params: dict = {"type": "artist", "limit": limit}
        if after:
            params["after"] = after
        data = await client.get("/me/following", params=params)
        artists_page = data.get("artists", {}) or {}
        items = artists_page.get("items", []) or []
        total = artists_page.get("total")
        lines = []
        for a in items:
            genres = ", ".join(a.get("genres", [])[:3]) or "N/A"
            lines.append(f"- {a.get('name')} ({genres}) (ID: {a.get('id')})")
        cursors = artists_page.get("cursors") or {}
        header = f"Followed artists ({len(items)}"
        if total is not None:
            header += f" of {total}"
        header += "):"
        body = "\n".join(lines) if lines else "  (none)"
        footer = ""
        if cursors.get("after"):
            footer = f"\n\nNext cursor (pass as `after`): {cursors['after']}"
        return f"{header}\n{body}{footer}"

    @mcp.tool()
    async def follow_artists_or_users(follow_type: str, ids: list[str]) -> str:
        """Follow one or more artists or users. Auto-chunks at 50 IDs per request.

        Args:
            follow_type: "artist" or "user".
            ids: List of Spotify artist or user IDs (not URIs).
        """
        err = _validate_type(follow_type)
        if err:
            return err
        if not ids:
            return "No IDs provided."
        followed = 0
        for chunk in chunked(ids, _FOLLOWING_MAX_PER_REQUEST):
            await client.put(
                "/me/following",
                params={"type": follow_type, "ids": ",".join(chunk)},
            )
            followed += len(chunk)
        return f"Now following {followed} {follow_type}(s)."

    @mcp.tool()
    async def unfollow_artists_or_users(follow_type: str, ids: list[str]) -> str:
        """Unfollow one or more artists or users. Auto-chunks at 50 IDs per request.

        Args:
            follow_type: "artist" or "user".
            ids: List of Spotify artist or user IDs (not URIs).
        """
        err = _validate_type(follow_type)
        if err:
            return err
        if not ids:
            return "No IDs provided."
        unfollowed = 0
        for chunk in chunked(ids, _FOLLOWING_MAX_PER_REQUEST):
            await client.delete(
                "/me/following",
                params={"type": follow_type, "ids": ",".join(chunk)},
            )
            unfollowed += len(chunk)
        return f"Unfollowed {unfollowed} {follow_type}(s)."

    @mcp.tool()
    async def check_following(follow_type: str, ids: list[str]) -> str:
        """Check whether the current user follows the given artists or users.

        Auto-chunks at 50 IDs per request.

        Args:
            follow_type: "artist" or "user".
            ids: List of Spotify artist or user IDs (not URIs).
        """
        err = _validate_type(follow_type)
        if err:
            return err
        if not ids:
            return "No IDs provided."
        combined: list[bool] = []
        for chunk in chunked(ids, _FOLLOWING_MAX_PER_REQUEST):
            data = await client.get(
                "/me/following/contains",
                params={"type": follow_type, "ids": ",".join(chunk)},
            )
            if isinstance(data, list):
                combined.extend(bool(v) for v in data)
            else:
                return f"Unexpected response: {data}"
        lines = [
            f"  {id_}: {'following' if following else 'not following'}"
            for id_, following in zip(ids, combined, strict=False)
        ]
        return f"Follow check ({follow_type}):\n" + "\n".join(lines)

    @mcp.tool()
    async def follow_playlist(playlist_id: str, public: bool = True) -> str:
        """Follow a playlist.

        Args:
            playlist_id: The Spotify ID of the playlist.
            public: True to make the playlist appear on the user's public profile (default True).
        """
        await client.put(
            f"/playlists/{playlist_id}/followers",
            json={"public": public},
        )
        return f"Now following playlist {playlist_id} (public={public})."

    @mcp.tool()
    async def unfollow_playlist(playlist_id: str) -> str:
        """Unfollow a playlist.

        Args:
            playlist_id: The Spotify ID of the playlist.
        """
        await client.delete(f"/playlists/{playlist_id}/followers")
        return f"Unfollowed playlist {playlist_id}."
