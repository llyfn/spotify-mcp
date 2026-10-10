from __future__ import annotations

import os
import sys
from pathlib import Path

SPOTIFY_API_BASE = "https://api.spotify.com/v1"
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"

CREDENTIALS_DIR = Path.home() / ".spotify-mcp"
CREDENTIALS_FILE = CREDENTIALS_DIR / "credentials.json"

DEFAULT_REDIRECT_URI = "http://127.0.0.1:8888/callback"

ALL_SCOPES = " ".join(
    [
        # User
        "user-read-private",
        # Playback
        "user-read-playback-state",
        "user-modify-playback-state",
        "user-read-currently-playing",
        "user-read-recently-played",
        # Library
        "user-library-read",
        "user-library-modify",
        # Listening history
        "user-top-read",
        "user-read-playback-position",
        # Playlists
        "playlist-read-private",
        "playlist-modify-public",
        "playlist-modify-private",
        # Follow
        "user-follow-read",
        "user-follow-modify",
    ]
)


def get_client_id() -> str:
    return os.environ["SPOTIFY_CLIENT_ID"]


def get_client_secret() -> str:
    return os.environ["SPOTIFY_CLIENT_SECRET"]


def get_redirect_uri() -> str:
    return os.environ.get("SPOTIFY_REDIRECT_URI", DEFAULT_REDIRECT_URI)


MIN_AUTH_TOKEN_LENGTH = 32


def get_mcp_auth_token() -> str | None:
    return os.environ.get("SPOTIFY_MCP_AUTH_TOKEN", "").strip() or None


def validate_http_environment() -> None:
    """Exit with a helpful error if the HTTP transport settings are invalid or unsafe."""
    errors: list[str] = []
    token = get_mcp_auth_token()
    if token is not None and len(token) < MIN_AUTH_TOKEN_LENGTH:
        errors.append(
            f"SPOTIFY_MCP_AUTH_TOKEN must be at least {MIN_AUTH_TOKEN_LENGTH} characters. "
            'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"'
        )
    if token is not None and not token.isascii():
        errors.append("SPOTIFY_MCP_AUTH_TOKEN must contain only ASCII characters.")
    if errors:
        for error in errors:
            print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


def validate_environment() -> None:
    """Exit with a helpful error if required env vars are missing."""
    missing = [
        var for var in ("SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET") if not os.environ.get(var)
    ]
    if missing:
        print(
            f"Error: missing required environment variable(s): {', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)
