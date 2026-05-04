from __future__ import annotations


class SpotifyMCPError(Exception):
    """Base exception for all Spotify MCP errors."""


class AuthenticationError(SpotifyMCPError):
    """Raised when authentication fails or tokens are invalid."""


class SpotifyAPIError(SpotifyMCPError):
    """Raised when the Spotify API returns an error response."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"Spotify API error {status_code}: {message}")
