from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from spotify_mcp.client import SpotifyClient


def register(mcp: FastMCP, client: SpotifyClient) -> None:
    @mcp.tool()
    async def follow(uris: list[str]) -> str:
        """Follow artists or users by saving them to your library.

        Args:
            uris: List of Spotify URIs (e.g. ["spotify:artist:xxx"]). Max 40.
        """
        await client.put("/me/library", params={"uris": ",".join(uris)})
        return f"Now following {len(uris)} item(s)."

    @mcp.tool()
    async def unfollow(uris: list[str]) -> str:
        """Unfollow artists or users by removing them from your library.

        Args:
            uris: List of Spotify URIs (e.g. ["spotify:artist:xxx"]). Max 40.
        """
        await client.delete("/me/library", params={"uris": ",".join(uris)})
        return f"Unfollowed {len(uris)} item(s)."

    @mcp.tool()
    async def check_following(uris: list[str]) -> str:
        """Check if items are saved in your library (artists, users, etc.).

        Args:
            uris: List of Spotify URIs to check (e.g. ["spotify:artist:xxx"]). Max 40.
        """
        data = await client.get(
            "/me/library/contains",
            params={"uris": ",".join(uris)},
        )
        if isinstance(data, list):
            results = [
                f"  {uri}: {'following' if following else 'not following'}"
                for uri, following in zip(uris, data, strict=False)
            ]
            return "Follow status:\n" + "\n".join(results)
        return f"Follow check result: {data}"
