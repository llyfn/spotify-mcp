from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Register canned prompts that drive common Spotify workflows."""

    @mcp.prompt()
    def build_playlist_from_recent(n_tracks: int = 30) -> str:
        """Build a new playlist from the user's recent listening."""
        return (
            f"Use the Spotify tools to build a new playlist of {n_tracks} tracks "
            "inspired by what I've been listening to lately. Steps:\n"
            "1. Call `get_recently_played` to see what I've played recently.\n"
            "2. Call `get_my_top_items` (item_type=tracks, time_range=short_term) "
            "to find what I've been hooked on this month.\n"
            "3. Identify recurring artists and a few standout tracks. Search with "
            "filters like `artist:...` to surface adjacent material I might have missed.\n"
            "4. Propose a playlist name and a short description, then ask me to "
            "confirm before calling `create_playlist`.\n"
            "5. After I confirm, create it and add the tracks via "
            "`add_playlist_items`. Report the playlist URL at the end."
        )

    @mcp.prompt()
    def weekly_listening_summary() -> str:
        """Summarize what the user listened to in the past week."""
        return (
            "Summarize my listening from the past week. Steps:\n"
            "1. Call `get_recently_played` with `limit=50` (the max). Use the "
            "`after` cursor (Unix-ms ~7 days ago) if available; otherwise work "
            "from the most recent 50.\n"
            "2. Group plays by artist and by album. Highlight what dominated.\n"
            "3. Pull `get_my_top_items` with `time_range=short_term` to compare "
            "against my 4-week trend.\n"
            "4. Write a tight 2-3 paragraph summary covering: top artists, any "
            "new music I tried, and any patterns worth pointing out. Use the "
            "actual track and artist names from the tool output."
        )

    @mcp.prompt()
    def playlist_from_artists(artists: str, tracks_per_artist: int = 5) -> str:
        """Build a playlist seeded by a comma-separated list of artists.

        Args:
            artists: Comma-separated list of artist names.
            tracks_per_artist: How many tracks to pull per artist (default 5).
        """
        return (
            f"Build a playlist seeded by these artists: {artists}.\n"
            f"For each artist, pick about {tracks_per_artist} representative tracks "
            "(prefer popular ones unless the user already knows them).\n"
            "Steps:\n"
            "1. For each artist name, call `search` (types=artist, limit=1) to "
            "get the canonical artist ID.\n"
            "2. For each ID, call `get_artist_albums` (include_groups=album,single) "
            "and pick tracks from the highest-rated or most recent material.\n"
            "3. Interleave the artists so the playlist doesn't run all of one "
            "artist in a row.\n"
            "4. Ask me for a name, then call `create_playlist` and "
            "`add_playlist_items` to assemble it. Report the URL."
        )

    @mcp.prompt()
    def library_cleanup(scan_size: int = 100) -> str:
        """Review the user's saved library and suggest cleanup candidates.

        Args:
            scan_size: How many recently-saved tracks to scan (default 100).
        """
        return (
            f"Help me prune my Spotify library. Scan the {scan_size} most recently "
            "saved tracks via `get_saved_tracks` (paginate with `offset` as needed).\n"
            "Steps:\n"
            "1. Look for duplicates (same title and artists; or remasters of the "
            "same recording).\n"
            "2. Look for tracks I likely saved by accident — single plays months "
            "ago, possibly from a one-off mood. Cross-check with "
            "`get_recently_played` to see if I've actually returned to them.\n"
            "3. Group your suggestions: 'clear duplicates', 'likely accidental', "
            "'consider revisiting'. Show track names and IDs so I can decide.\n"
            "4. DO NOT call `remove_from_library` until I explicitly confirm a "
            "specific list."
        )
