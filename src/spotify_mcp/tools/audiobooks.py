from __future__ import annotations

from typing import TYPE_CHECKING

from spotify_mcp.tools._utils import paged_list

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from spotify_mcp.client import SpotifyClient


def register(mcp: FastMCP, client: SpotifyClient) -> None:
    @mcp.tool()
    async def get_audiobook(audiobook_id: str) -> str:
        """Get details of a Spotify audiobook.

        Args:
            audiobook_id: The Spotify ID of the audiobook.
        """
        data = await client.get(f"/audiobooks/{audiobook_id}")
        authors = ", ".join(a["name"] for a in data.get("authors", []))
        narrators = ", ".join(n["name"] for n in data.get("narrators", []))
        return (
            f"Audiobook: {data.get('name')}\n"
            f"Author(s): {authors}\n"
            f"Narrator(s): {narrators}\n"
            f"Publisher: {data.get('publisher', 'Unknown')}\n"
            f"Description: {data.get('description', 'N/A')}\n"
            f"Total Chapters: {data.get('total_chapters', 'N/A')}\n"
            f"Languages: {', '.join(data.get('languages', []))}\n"
            f"URL: {data.get('external_urls', {}).get('spotify', 'N/A')}"
        )

    @mcp.tool()
    async def get_audiobook_chapters(audiobook_id: str, limit: int = 20, offset: int = 0) -> str:
        """Get chapters of a Spotify audiobook.

        Args:
            audiobook_id: The Spotify ID of the audiobook.
            limit: Maximum number of chapters to return (1-50, default 20).
            offset: Index of the first chapter to return (default 0).
        """
        data = await client.get(
            f"/audiobooks/{audiobook_id}/chapters",
            params={"limit": limit, "offset": offset},
        )
        items = data.get("items", [])
        lines = []
        for i, ch in enumerate(items, start=offset + 1):
            duration_ms = ch.get("duration_ms", 0)
            duration = f"{duration_ms // 60000}min"
            lines.append(f"{i}. {ch.get('name')} ({duration}) (ID: {ch.get('id')})")
        total = data.get("total", len(items))
        return paged_list("Chapters", lines, total, offset)

    @mcp.tool()
    async def get_chapter(chapter_id: str) -> str:
        """Get details of a specific audiobook chapter.

        Args:
            chapter_id: The Spotify ID of the chapter.
        """
        data = await client.get(f"/chapters/{chapter_id}")
        duration_ms = data.get("duration_ms", 0)
        duration = f"{duration_ms // 60000}:{(duration_ms % 60000) // 1000:02d}"
        audiobook = data.get("audiobook", {})
        return (
            f"Chapter: {data.get('name')}\n"
            f"Audiobook: {audiobook.get('name', 'N/A')}\n"
            f"Chapter Number: {data.get('chapter_number', 'N/A')}\n"
            f"Duration: {duration}\n"
            f"Description: {data.get('description', 'N/A')}\n"
            f"URL: {data.get('external_urls', {}).get('spotify', 'N/A')}"
        )
