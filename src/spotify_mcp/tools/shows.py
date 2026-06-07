from __future__ import annotations

from typing import TYPE_CHECKING

from spotify_mcp.tools._utils import format_duration_min, paged_list

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from spotify_mcp.client import SpotifyClient


_SHOWS_MAX_IDS = 50
_EPISODES_MAX_IDS = 50


def register(mcp: FastMCP, client: SpotifyClient) -> None:
    @mcp.tool()
    async def get_show(show_id: str, market: str | None = None) -> str:
        """Get details of a Spotify show (podcast).

        Args:
            show_id: The Spotify ID of the show.
            market: ISO 3166-1 alpha-2 country code; affects availability.
        """
        params = {"market": market} if market else None
        data = await client.get(f"/shows/{show_id}", params=params)
        episodes = data.get("episodes", {}).get("items", [])
        episode_lines = []
        for i, ep in enumerate(episodes[:10], start=1):
            episode_lines.append(f"  {i}. {ep.get('name')} ({ep.get('release_date', 'N/A')})")
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
    async def get_shows(show_ids: list[str], market: str | None = None) -> str:
        """Get details of multiple shows in one call (up to 50 IDs).

        Args:
            show_ids: List of Spotify show IDs (max 50).
            market: ISO 3166-1 alpha-2 country code.
        """
        if not show_ids:
            return "No show IDs provided."
        if len(show_ids) > _SHOWS_MAX_IDS:
            return f"Too many IDs: {len(show_ids)}. Max is {_SHOWS_MAX_IDS}."
        params: dict = {"ids": ",".join(show_ids)}
        if market:
            params["market"] = market
        data = await client.get("/shows", params=params)
        shows = data.get("shows", [])
        lines = []
        for s in shows:
            if not s:
                lines.append("- (not found)")
                continue
            lines.append(
                f"- {s.get('name')} by {s.get('publisher', 'Unknown')} (ID: {s.get('id')})"
            )
        return f"Shows ({len(lines)}):\n" + "\n".join(lines)

    @mcp.tool()
    async def get_show_episodes(
        show_id: str,
        limit: int = 20,
        offset: int = 0,
        market: str | None = None,
    ) -> str:
        """Get episodes of a Spotify show.

        Args:
            show_id: The Spotify ID of the show.
            limit: Maximum number of episodes to return (1-50, default 20).
            offset: Index of the first episode to return (default 0).
            market: ISO 3166-1 alpha-2 country code.
        """
        params: dict = {"limit": limit, "offset": offset}
        if market:
            params["market"] = market
        data = await client.get(f"/shows/{show_id}/episodes", params=params)
        items = data.get("items", [])
        lines = []
        for i, ep in enumerate(items, start=offset + 1):
            duration = format_duration_min(ep.get("duration_ms", 0))
            release = ep.get("release_date", "N/A")
            lines.append(f"{i}. {ep.get('name')} ({release}, {duration}) (ID: {ep.get('id')})")
        total = data.get("total", len(items))
        return paged_list("Episodes", lines, total, offset)

    @mcp.tool()
    async def get_episode(episode_id: str, market: str | None = None) -> str:
        """Get details of a podcast episode.

        Args:
            episode_id: The Spotify ID of the episode.
            market: ISO 3166-1 alpha-2 country code.
        """
        params = {"market": market} if market else None
        data = await client.get(f"/episodes/{episode_id}", params=params)
        show = data.get("show") or {}
        duration = format_duration_min(data.get("duration_ms", 0))
        lines = [
            f"Episode: {data.get('name')}",
            f"Show: {show.get('name', 'N/A')} (by {show.get('publisher', 'Unknown')})",
            f"Release Date: {data.get('release_date', 'N/A')}",
            f"Duration: {duration}",
            f"Description: {data.get('description', 'N/A')}",
            f"Explicit: {data.get('explicit', False)}",
            f"URL: {data.get('external_urls', {}).get('spotify', 'N/A')}",
        ]
        return "\n".join(lines)

    @mcp.tool()
    async def get_episodes(episode_ids: list[str], market: str | None = None) -> str:
        """Get details of multiple episodes in one call (up to 50 IDs).

        Args:
            episode_ids: List of Spotify episode IDs (max 50).
            market: ISO 3166-1 alpha-2 country code.
        """
        if not episode_ids:
            return "No episode IDs provided."
        if len(episode_ids) > _EPISODES_MAX_IDS:
            return f"Too many IDs: {len(episode_ids)}. Max is {_EPISODES_MAX_IDS}."
        params: dict = {"ids": ",".join(episode_ids)}
        if market:
            params["market"] = market
        data = await client.get("/episodes", params=params)
        episodes = data.get("episodes", [])
        lines = []
        for ep in episodes:
            if not ep:
                lines.append("- (not found)")
                continue
            show = ep.get("show") or {}
            release = ep.get("release_date", "N/A")
            lines.append(
                f"- {ep.get('name')} on {show.get('name', 'N/A')} ({release}) (ID: {ep.get('id')})"
            )
        return f"Episodes ({len(lines)}):\n" + "\n".join(lines)
