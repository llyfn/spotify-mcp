from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from spotify_mcp.client import SpotifyClient


def register(mcp: FastMCP, client: SpotifyClient) -> None:
    @mcp.tool()
    async def get_show(show_id: str) -> str:
        """Get details of a Spotify show (podcast).

        Args:
            show_id: The Spotify ID of the show.
        """
        data = await client.get(f"/shows/{show_id}")
        episodes = data.get("episodes", {}).get("items", [])
        episode_lines = []
        for i, ep in enumerate(episodes[:10], start=1):
            episode_lines.append(
                f"  {i}. {ep.get('name')} ({ep.get('release_date', 'N/A')})"
            )
        lines = [f"Show: {data.get('name')}"]
        if data.get("publisher"):
            lines.append(f"Publisher: {data['publisher']}")
        lines.append(f"Description: {data.get('description', 'N/A')}")
        lines.append(f"Total Episodes: {data.get('total_episodes', 'N/A')}")
        if data.get("languages"):
            lines.append(f"Languages: {', '.join(data['languages'])}")
        lines.append(f"Explicit: {data.get('explicit', False)}")
        lines.append(f"URL: {data.get('external_urls', {}).get('spotify', 'N/A')}")
        result = "\n".join(lines)
        if episode_lines:
            result += "\n\nRecent episodes:\n" + "\n".join(episode_lines)
        return result

    @mcp.tool()
    async def get_show_episodes(
        show_id: str, limit: int = 20, offset: int = 0
    ) -> str:
        """Get episodes of a Spotify show.

        Args:
            show_id: The Spotify ID of the show.
            limit: Maximum number of episodes to return (1-50, default 20).
            offset: Index of the first episode to return (default 0).
        """
        data = await client.get(
            f"/shows/{show_id}/episodes",
            params={"limit": limit, "offset": offset},
        )
        items = data.get("items", [])
        lines = []
        for i, ep in enumerate(items, start=offset + 1):
            duration_ms = ep.get("duration_ms", 0)
            duration = f"{duration_ms // 60000}min"
            release = ep.get("release_date", "N/A")
            lines.append(
                f"{i}. {ep.get('name')} ({release}, {duration}) (ID: {ep.get('id')})"
            )
        total = data.get("total", len(items))
        return (
            f"Episodes (showing {offset + 1}-{offset + len(items)} of {total}):\n"
            + "\n".join(lines)
        )
