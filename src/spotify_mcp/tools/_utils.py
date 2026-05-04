from __future__ import annotations


def paged_list(label: str, lines: list[str], total: int, offset: int) -> str:
    """Format a paginated list for tool output."""
    n = len(lines)
    return f"{label} (showing {offset + 1}-{offset + n} of {total}):\n" + "\n".join(lines)
