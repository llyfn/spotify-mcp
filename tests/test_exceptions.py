from __future__ import annotations

from spotify_mcp.exceptions import (
    AuthenticationError,
    SpotifyAPIError,
    SpotifyMCPError,
)


def test_spotify_api_error_message_includes_status_and_message() -> None:
    err = SpotifyAPIError(404, "Not found")
    assert err.status_code == 404
    assert err.message == "Not found"
    assert str(err) == "Spotify API error 404: Not found"


def test_spotify_api_error_is_spotify_mcp_error() -> None:
    assert issubclass(SpotifyAPIError, SpotifyMCPError)


def test_authentication_error_is_spotify_mcp_error() -> None:
    assert issubclass(AuthenticationError, SpotifyMCPError)
    err = AuthenticationError("bad token")
    assert str(err) == "bad token"
