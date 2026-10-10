from __future__ import annotations

from typing import TYPE_CHECKING

from spotify_mcp.tools._utils import (
    UNAVAILABLE,
    format_duration_min,
    format_duration_mmss,
    paged_list,
)

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from spotify_mcp.client import SpotifyClient


def register(mcp: FastMCP, client: SpotifyClient) -> None:
    @mcp.tool()
    async def get_audiobook(audiobook_id: str, market: str | None = None) -> str:
        """Get details of a Spotify audiobook.

        Args:
            audiobook_id: The Spotify ID of the audiobook.
            market: ISO 3166-1 alpha-2 country code.
        """
        params = {"market": market} if market else None
        data = await client.get(f"/audiobooks/{audiobook_id}", params=params)
        authors = ", ".join(a["name"] for a in data.get("authors", []))
        narrators = ", ".join(n["name"] for n in data.get("narrators", []))
        return (
            f"Audiobook: {data.get('name')}\n"
            f"Author(s): {authors}\n"
            f"Narrator(s): {narrators}\n"
            f"Description: {data.get('description', 'N/A')}\n"
            f"Total Chapters: {data.get('total_chapters', 'N/A')}\n"
            f"Languages: {', '.join(data.get('languages', []))}\n"
            f"URL: {data.get('external_urls', {}).get('spotify', 'N/A')}"
        )

    @mcp.tool()
    async def get_audiobook_chapters(
        audiobook_id: str,
        limit: int = 20,
        offset: int = 0,
        market: str | None = None,
    ) -> str:
        """Get chapters of a Spotify audiobook.

        Args:
            audiobook_id: The Spotify ID of the audiobook.
            limit: Maximum number of chapters to return (1-50, default 20).
            offset: Index of the first chapter to return (default 0).
            market: ISO 3166-1 alpha-2 country code.
        """
        params: dict = {"limit": limit, "offset": offset}
        if market:
            params["market"] = market
        data = await client.get(f"/audiobooks/{audiobook_id}/chapters", params=params)
        items = data.get("items", [])
        lines = []
        for i, ch in enumerate(items, start=offset + 1):
            if not ch:
                lines.append(f"{i}. {UNAVAILABLE}")
                continue
            duration = format_duration_min(ch.get("duration_ms", 0))
            lines.append(f"{i}. {ch.get('name')} ({duration}) (ID: {ch.get('id')})")
        total = data.get("total", len(items))
        return paged_list("Chapters", lines, total, offset)

    @mcp.tool()
    async def get_chapter(chapter_id: str, market: str | None = None) -> str:
        """Get details of a specific audiobook chapter.

        Args:
            chapter_id: The Spotify ID of the chapter.
            market: ISO 3166-1 alpha-2 country code.
        """
        params = {"market": market} if market else None
        data = await client.get(f"/chapters/{chapter_id}", params=params)
        duration = format_duration_mmss(data.get("duration_ms", 0))
        audiobook = data.get("audiobook", {})
        return (
            f"Chapter: {data.get('name')}\n"
            f"Audiobook: {audiobook.get('name', 'N/A')}\n"
            f"Chapter Number: {data.get('chapter_number', 'N/A')}\n"
            f"Duration: {duration}\n"
            f"Description: {data.get('description', 'N/A')}\n"
            f"URL: {data.get('external_urls', {}).get('spotify', 'N/A')}"
        )
