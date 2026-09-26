from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from spotify_mcp.client import SpotifyClient


def register(mcp: FastMCP, client: SpotifyClient) -> None:
    @mcp.tool()
    async def get_followed_artists(limit: int = 20, after: str | None = None) -> str:
        """Get the current user's followed artists. Cursor-paginated.

        To follow or unfollow, use `save_to_library` / `remove_from_library` with Spotify URIs.

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
