from __future__ import annotations

from typing import TYPE_CHECKING

from spotify_mcp.tools._utils import chunked, paged_list

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from spotify_mcp.client import SpotifyClient


_LIBRARY_MAX_PER_REQUEST = 50


def register(mcp: FastMCP, client: SpotifyClient) -> None:
    @mcp.tool()
    async def get_saved_tracks(limit: int = 20, offset: int = 0) -> str:
        """Get the current user's saved tracks.

        Args:
            limit: Maximum number of tracks to return (1-50, default 20).
            offset: Index of the first track to return (default 0).
        """
        data = await client.get("/me/tracks", params={"limit": limit, "offset": offset})
        items = data.get("items", [])
        lines = []
        for i, item in enumerate(items, start=offset + 1):
            track = item.get("track", {})
            artists = ", ".join(a["name"] for a in track.get("artists", []))
            lines.append(f"{i}. {track.get('name')} - {artists} (ID: {track.get('id')})")
        total = data.get("total", len(items))
        return paged_list("Saved tracks", lines, total, offset)

    @mcp.tool()
    async def get_saved_albums(limit: int = 20, offset: int = 0) -> str:
        """Get the current user's saved albums.

        Args:
            limit: Maximum number of albums to return (1-50, default 20).
            offset: Index of the first album to return (default 0).
        """
        data = await client.get("/me/albums", params={"limit": limit, "offset": offset})
        items = data.get("items", [])
        lines = []
        for item in items:
            album = item.get("album", {})
            artists = ", ".join(a["name"] for a in album.get("artists", []))
            release = album.get("release_date", "N/A")
            lines.append(f"- {album.get('name')} by {artists} ({release}) (ID: {album.get('id')})")
        total = data.get("total", len(items))
        return paged_list("Saved albums", lines, total, offset)

    @mcp.tool()
    async def get_saved_shows(limit: int = 20, offset: int = 0) -> str:
        """Get the current user's saved shows (podcasts).

        Args:
            limit: Maximum number of shows to return (1-50, default 20).
            offset: Index of the first show to return (default 0).
        """
        data = await client.get("/me/shows", params={"limit": limit, "offset": offset})
        items = data.get("items", [])
        lines = []
        for item in items:
            show = item.get("show", {})
            lines.append(
                f"- {show.get('name')} by {show.get('publisher', 'Unknown')} (ID: {show.get('id')})"
            )
        total = data.get("total", len(items))
        return paged_list("Saved shows", lines, total, offset)

    @mcp.tool()
    async def get_saved_episodes(limit: int = 20, offset: int = 0) -> str:
        """Get the current user's saved episodes.

        Args:
            limit: Maximum number of episodes to return (1-50, default 20).
            offset: Index of the first episode to return (default 0).
        """
        data = await client.get("/me/episodes", params={"limit": limit, "offset": offset})
        items = data.get("items", [])
        lines = []
        for item in items:
            episode = item.get("episode", {})
            release = episode.get("release_date", "N/A")
            lines.append(f"- {episode.get('name')} ({release}) (ID: {episode.get('id')})")
        total = data.get("total", len(items))
        return paged_list("Saved episodes", lines, total, offset)

    @mcp.tool()
    async def get_saved_audiobooks(limit: int = 20, offset: int = 0) -> str:
        """Get the current user's saved audiobooks.

        Args:
            limit: Maximum number of audiobooks to return (1-50, default 20).
            offset: Index of the first audiobook to return (default 0).
        """
        data = await client.get("/me/audiobooks", params={"limit": limit, "offset": offset})
        items = data.get("items", [])
        lines = []
        for item in items:
            authors = ", ".join(a["name"] for a in item.get("authors", []))
            lines.append(f"- {item.get('name')} by {authors} (ID: {item.get('id')})")
        total = data.get("total", len(items))
        return paged_list("Saved audiobooks", lines, total, offset)

    @mcp.tool()
    async def save_to_library(uris: list[str]) -> str:
        """Save items (tracks/albums/shows/episodes/audiobooks) to the user's library.

        Auto-chunks at 50 items per request.

        Args:
            uris: List of Spotify URIs to save (e.g. ["spotify:track:xxx"]).
        """
        if not uris:
            return "No URIs provided."
        saved = 0
        for chunk in chunked(uris, _LIBRARY_MAX_PER_REQUEST):
            await client.put("/me/library", params={"uris": ",".join(chunk)})
            saved += len(chunk)
        return f"Saved {saved} item(s) to your library."

    @mcp.tool()
    async def remove_from_library(uris: list[str]) -> str:
        """Remove items from the current user's library. Auto-chunks at 50 items per request.

        Args:
            uris: List of Spotify URIs to remove (e.g. ["spotify:track:xxx"]).
        """
        if not uris:
            return "No URIs provided."
        removed = 0
        for chunk in chunked(uris, _LIBRARY_MAX_PER_REQUEST):
            await client.delete("/me/library", params={"uris": ",".join(chunk)})
            removed += len(chunk)
        return f"Removed {removed} item(s) from your library."

    @mcp.tool()
    async def check_saved_in_library(uris: list[str]) -> str:
        """Check if items are saved in the current user's library.

        Auto-chunks at 50 items per request.

        Args:
            uris: List of Spotify URIs to check (e.g. ["spotify:track:xxx"]).
        """
        if not uris:
            return "No URIs provided."
        combined: list[bool] = []
        for chunk in chunked(uris, _LIBRARY_MAX_PER_REQUEST):
            data = await client.get("/me/library/contains", params={"uris": ",".join(chunk)})
            if isinstance(data, list):
                combined.extend(bool(v) for v in data)
            else:
                return f"Library check result: {data}"
        results = [
            f"  {uri}: {'saved' if saved else 'not saved'}"
            for uri, saved in zip(uris, combined, strict=False)
        ]
        return "Library check:\n" + "\n".join(results)
