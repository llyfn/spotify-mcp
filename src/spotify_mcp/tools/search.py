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
            tracks = data["tracks"].get("items", [])
            if tracks:
                lines = []
                for t in tracks:
                    artists = ", ".join(a["name"] for a in t.get("artists", []))
                    lines.append(
                        f"  - {t['name']} by {artists} (ID: {t['id']})"
                    )
                sections.append(
                    f"Tracks ({data['tracks'].get('total', 0)} total):\n" + "\n".join(lines)
                )

        if "albums" in data:
            albums = data["albums"].get("items", [])
            if albums:
                lines = []
                for a in albums:
                    artists = ", ".join(ar["name"] for ar in a.get("artists", []))
                    release = a.get("release_date", "N/A")
                    lines.append(
                        f"  - {a['name']} by {artists} ({release}) (ID: {a['id']})"
                    )
                sections.append(
                    f"Albums ({data['albums'].get('total', 0)} total):\n" + "\n".join(lines)
                )

        if "artists" in data:
            artists_list = data["artists"].get("items", [])
            if artists_list:
                lines = []
                for a in artists_list:
                    followers = a.get("followers", {}).get("total", 0)
                    lines.append(
                        f"  - {a['name']} ({followers:,} followers) (ID: {a['id']})"
                    )
                sections.append(
                    f"Artists ({data['artists'].get('total', 0)} total):\n" + "\n".join(lines)
                )

        if "playlists" in data:
            playlists = data["playlists"].get("items", [])
            if playlists:
                lines = []
                for p in playlists:
                    owner = p.get("owner", {}).get("display_name", "Unknown")
                    lines.append(f"  - {p['name']} by {owner} (ID: {p['id']})")
                sections.append(
                    f"Playlists ({data['playlists'].get('total', 0)} total):\n" + "\n".join(lines)
                )

        if "shows" in data:
            shows = data["shows"].get("items", [])
            if shows:
                lines = [
                    f"  - {s['name']} by {s.get('publisher', 'Unknown')} (ID: {s['id']})"
                    for s in shows
                ]
                sections.append(
                    f"Shows ({data['shows'].get('total', 0)} total):\n" + "\n".join(lines)
                )

        if "episodes" in data:
            episodes = data["episodes"].get("items", [])
            if episodes:
                lines = [
                    f"  - {e['name']} ({e.get('release_date', 'N/A')}) (ID: {e['id']})"
                    for e in episodes
                ]
                sections.append(
                    f"Episodes ({data['episodes'].get('total', 0)} total):\n" + "\n".join(lines)
                )

        if "audiobooks" in data:
            audiobooks = data["audiobooks"].get("items", [])
            if audiobooks:
                lines = []
                for ab in audiobooks:
                    authors = ", ".join(a["name"] for a in ab.get("authors", []))
                    lines.append(f"  - {ab['name']} by {authors} (ID: {ab['id']})")
                sections.append(
                    f"Audiobooks ({data['audiobooks'].get('total', 0)} total):\n"
                    + "\n".join(lines)
                )

        if not sections:
            return "No results found."

        return "\n\n".join(sections)
