from __future__ import annotations

from typing import TYPE_CHECKING

from spotify_mcp.tools._utils import paged_list

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from spotify_mcp.client import SpotifyClient


def register(mcp: FastMCP, client: SpotifyClient) -> None:
    @mcp.tool()
    async def get_my_profile() -> str:
        """Get the current user's Spotify profile."""
        data = await client.get("/me")
        return (
            f"User: {data.get('display_name', 'N/A')}\n"
            f"ID: {data.get('id')}\n"
            f"Email: {data.get('email', 'N/A')}\n"
            f"Country: {data.get('country', 'N/A')}\n"
            f"Product: {data.get('product', 'N/A')}\n"
            f"Followers: {data.get('followers', {}).get('total', 0):,}\n"
            f"URL: {data.get('external_urls', {}).get('spotify', 'N/A')}"
        )

    @mcp.tool()
    async def get_my_top_items(
        item_type: str = "tracks",
        time_range: str = "medium_term",
        limit: int = 20,
        offset: int = 0,
    ) -> str:
        """Get the current user's top artists or tracks.

        Args:
            item_type: Type of items: "artists" or "tracks" (default "tracks").
            time_range: "short_term" (~4wk), "medium_term" (~6mo), or "long_term" (all time).
            limit: Maximum number of items to return (1-50, default 20).
            offset: Index of the first item to return (default 0).
        """
        data = await client.get(
            f"/me/top/{item_type}",
            params={"time_range": time_range, "limit": limit, "offset": offset},
        )
        items = data.get("items", [])
        lines = []
        for i, item in enumerate(items, start=offset + 1):
            if item_type == "artists":
                genres = ", ".join(item.get("genres", [])[:3])
                lines.append(f"{i}. {item.get('name')} ({genres or 'N/A'}) (ID: {item.get('id')})")
            else:
                artists = ", ".join(a["name"] for a in item.get("artists", []))
                lines.append(f"{i}. {item.get('name')} - {artists} (ID: {item.get('id')})")
        total = data.get("total", len(items))
        range_label = {
            "short_term": "last 4 weeks",
            "medium_term": "last 6 months",
            "long_term": "all time",
        }.get(time_range, time_range)
        return paged_list(f"Top {item_type} ({range_label})", lines, total, offset)
