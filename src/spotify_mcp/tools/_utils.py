from __future__ import annotations

from collections.abc import Iterable


def paged_list(label: str, lines: list[str], total: int, offset: int) -> str:
    """Format a paginated list for tool output."""
    n = len(lines)
    return f"{label} (showing {offset + 1}-{offset + n} of {total}):\n" + "\n".join(lines)


def format_track(item: dict | None) -> str:
    """Format a track or episode object into a readable string.

    Handles both shapes:
      - track:   "Name by A, B (from Album) (ID: ...)"
      - episode: "Name on Show (ID: ...)"
    """
    if not item:
        return "Nothing playing"
    name = item.get("name", "Unknown")
    item_id = item.get("id")
    id_suffix = f" (ID: {item_id})" if item_id else ""

    # Episode shape: has a `show` object.
    show = item.get("show")
    if isinstance(show, dict) and show.get("name"):
        return f"{name} on {show['name']}{id_suffix}"

    artist_names = ", ".join(a["name"] for a in item.get("artists", []))
    album_name = (item.get("album") or {}).get("name", "")
    if artist_names:
        suffix = f" (from {album_name})" if album_name else ""
        return f"{name} by {artist_names}{suffix}{id_suffix}"
    return name + id_suffix


def format_progress(progress_ms: int | None, duration_ms: int | None) -> str:
    """Format progress/duration as M:SS / M:SS."""
    if progress_ms is None or duration_ms is None:
        return "N/A"
    p_min, p_sec = divmod(progress_ms // 1000, 60)
    d_min, d_sec = divmod(duration_ms // 1000, 60)
    return f"{p_min}:{p_sec:02d} / {d_min}:{d_sec:02d}"


def format_duration_mmss(duration_ms: int | None) -> str:
    """Format milliseconds as M:SS."""
    if not duration_ms:
        return "0:00"
    minutes, seconds = divmod(duration_ms // 1000, 60)
    return f"{minutes}:{seconds:02d}"


def format_duration_min(duration_ms: int | None) -> str:
    """Format milliseconds as 'Nmin' (used for shows/audiobook chapters)."""
    if not duration_ms:
        return "0min"
    return f"{duration_ms // 60000}min"


def chunked[T](items: Iterable[T], size: int) -> list[list[T]]:
    """Split a sequence into chunks of at most `size` items."""
    if size <= 0:
        raise ValueError("chunk size must be positive")
    seq = list(items)
    return [seq[i : i + size] for i in range(0, len(seq), size)]
