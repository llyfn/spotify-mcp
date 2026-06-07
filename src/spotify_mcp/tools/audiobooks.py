from __future__ import annotations

from typing import TYPE_CHECKING

from spotify_mcp.tools._utils import format_duration_min, format_duration_mmss, paged_list

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from spotify_mcp.client import SpotifyClient


_AUDIOBOOKS_MAX_IDS = 50
_CHAPTERS_MAX_IDS = 50


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
            f"Publisher: {data.get('publisher', 'Unknown')}\n"
            f"Description: {data.get('description', 'N/A')}\n"
            f"Total Chapters: {data.get('total_chapters', 'N/A')}\n"
            f"Languages: {', '.join(data.get('languages', []))}\n"
            f"URL: {data.get('external_urls', {}).get('spotify', 'N/A')}"
        )

    @mcp.tool()
    async def get_audiobooks(audiobook_ids: list[str], market: str | None = None) -> str:
        """Get details of multiple audiobooks in one call (up to 50 IDs).

        Args:
            audiobook_ids: List of Spotify audiobook IDs (max 50).
            market: ISO 3166-1 alpha-2 country code.
        """
        if not audiobook_ids:
            return "No audiobook IDs provided."
        if len(audiobook_ids) > _AUDIOBOOKS_MAX_IDS:
            return f"Too many IDs: {len(audiobook_ids)}. Max is {_AUDIOBOOKS_MAX_IDS}."
        params: dict = {"ids": ",".join(audiobook_ids)}
        if market:
            params["market"] = market
        data = await client.get("/audiobooks", params=params)
        audiobooks = data.get("audiobooks", [])
        lines = []
        for ab in audiobooks:
            if not ab:
                lines.append("- (not found)")
                continue
            authors = ", ".join(a["name"] for a in ab.get("authors", []))
            lines.append(f"- {ab.get('name')} by {authors} (ID: {ab.get('id')})")
        return f"Audiobooks ({len(lines)}):\n" + "\n".join(lines)

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

    @mcp.tool()
    async def get_chapters(chapter_ids: list[str], market: str | None = None) -> str:
        """Get details of multiple chapters in one call (up to 50 IDs).

        Args:
            chapter_ids: List of Spotify chapter IDs (max 50).
            market: ISO 3166-1 alpha-2 country code.
        """
        if not chapter_ids:
            return "No chapter IDs provided."
        if len(chapter_ids) > _CHAPTERS_MAX_IDS:
            return f"Too many IDs: {len(chapter_ids)}. Max is {_CHAPTERS_MAX_IDS}."
        params: dict = {"ids": ",".join(chapter_ids)}
        if market:
            params["market"] = market
        data = await client.get("/chapters", params=params)
        chapters = data.get("chapters", [])
        lines = []
        for ch in chapters:
            if not ch:
                lines.append("- (not found)")
                continue
            audiobook = ch.get("audiobook") or {}
            duration = format_duration_min(ch.get("duration_ms", 0))
            lines.append(
                f"- {ch.get('name')} from {audiobook.get('name', 'N/A')} "
                f"({duration}) (ID: {ch.get('id')})"
            )
        return f"Chapters ({len(lines)}):\n" + "\n".join(lines)
