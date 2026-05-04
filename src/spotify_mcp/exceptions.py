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


class RateLimitError(SpotifyAPIError):
    """Raised when rate limited (HTTP 429)."""

    def __init__(self, retry_after: int, message: str = "Rate limited") -> None:
        self.retry_after = retry_after
        super().__init__(429, message)


class NotFoundError(SpotifyAPIError):
    """Raised when a resource is not found (HTTP 404)."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(404, message)
