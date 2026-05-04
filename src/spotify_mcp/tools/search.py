from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from spotify_mcp.client import SpotifyClient


def register(mcp: FastMCP, client: SpotifyClient) -> None:
    @mcp.tool()
    async def search(
        query: str,
        types: str = "track",
        limit: int = 10,
        offset: int = 0,
        market: str | None = None,
    ) -> str:
        """Search for tracks, albums, artists, playlists, shows, episodes, or audiobooks on Spotify.

        Args:
            query: Search query. Supports filters: artist:, album:, track:, year:, genre:.
            types: Comma-separated types: track, album, artist, playlist, show, episode, audiobook.
            limit: Maximum results per type (1-50, default 10).
            offset: Index of first result to return (default 0).
            market: ISO 3166-1 alpha-2 country code to filter results.
        """
        params: dict = {
            "q": query,
            "type": types,
            "limit": limit,
            "offset": offset,
        }
        if market:
            params["market"] = market
        data = await client.get("/search", params=params)

        sections = []

        if "tracks" in data:
            track_items = data["tracks"].get("items", [])
            if track_items:
                lines = []
                for t in track_items:
                    artist_names = ", ".join(a["name"] for a in t.get("artists", []))
                    lines.append(f"  - {t['name']} by {artist_names} (ID: {t['id']})")
                sections.append(
                    f"Tracks ({data['tracks'].get('total', 0)} total):\n" + "\n".join(lines)
                )

        if "albums" in data:
            album_items = data["albums"].get("items", [])
            if album_items:
                lines = []
                for a in album_items:
                    artist_names = ", ".join(ar["name"] for ar in a.get("artists", []))
                    release = a.get("release_date", "N/A")
                    lines.append(f"  - {a['name']} by {artist_names} ({release}) (ID: {a['id']})")
                sections.append(
                    f"Albums ({data['albums'].get('total', 0)} total):\n" + "\n".join(lines)
                )

        if "artists" in data:
            artist_items = data["artists"].get("items", [])
            if artist_items:
                lines = []
                for a in artist_items:
                    followers = a.get("followers", {}).get("total", 0)
                    lines.append(f"  - {a['name']} ({followers:,} followers) (ID: {a['id']})")
                sections.append(
                    f"Artists ({data['artists'].get('total', 0)} total):\n" + "\n".join(lines)
                )

        if "playlists" in data:
            playlist_items = data["playlists"].get("items", [])
            if playlist_items:
                lines = []
                for p in playlist_items:
                    owner = p.get("owner", {}).get("display_name", "Unknown")
                    lines.append(f"  - {p['name']} by {owner} (ID: {p['id']})")
                sections.append(
                    f"Playlists ({data['playlists'].get('total', 0)} total):\n" + "\n".join(lines)
                )

        if "shows" in data:
            show_items = data["shows"].get("items", [])
            if show_items:
                lines = [
                    f"  - {s['name']} by {s.get('publisher', 'Unknown')} (ID: {s['id']})"
                    for s in show_items
                ]
                sections.append(
                    f"Shows ({data['shows'].get('total', 0)} total):\n" + "\n".join(lines)
                )

        if "episodes" in data:
            episode_items = data["episodes"].get("items", [])
            if episode_items:
                lines = [
                    f"  - {e['name']} ({e.get('release_date', 'N/A')}) (ID: {e['id']})"
                    for e in episode_items
                ]
                sections.append(
                    f"Episodes ({data['episodes'].get('total', 0)} total):\n" + "\n".join(lines)
                )

        if "audiobooks" in data:
            audiobook_items = data["audiobooks"].get("items", [])
            if audiobook_items:
                lines = []
                for ab in audiobook_items:
                    authors = ", ".join(a["name"] for a in ab.get("authors", []))
                    lines.append(f"  - {ab['name']} by {authors} (ID: {ab['id']})")
                sections.append(
                    f"Audiobooks ({data['audiobooks'].get('total', 0)} total):\n" + "\n".join(lines)
                )

        if not sections:
            return "No results found."

        return "\n\n".join(sections)
