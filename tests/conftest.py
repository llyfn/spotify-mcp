from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_credentials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Redirect credential storage to a temp dir so tests never touch ~/.spotify-mcp."""
    creds_dir = tmp_path / ".spotify-mcp"
    creds_file = creds_dir / "credentials.json"
    monkeypatch.setattr("spotify_mcp.config.CREDENTIALS_DIR", creds_dir)
    monkeypatch.setattr("spotify_mcp.config.CREDENTIALS_FILE", creds_file)
    monkeypatch.setattr("spotify_mcp.auth.CREDENTIALS_DIR", creds_dir)
    monkeypatch.setattr("spotify_mcp.auth.CREDENTIALS_FILE", creds_file)
    yield creds_dir


@pytest.fixture
def spotify_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide fake Spotify OAuth env vars."""
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "test-client-secret")
    monkeypatch.delenv("SPOTIFY_REDIRECT_URI", raising=False)


@pytest.fixture
def no_spotify_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure Spotify OAuth env vars are unset."""
    for var in ("SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "SPOTIFY_REDIRECT_URI"):
        monkeypatch.delenv(var, raising=False)
    # Belt-and-suspenders: in case test runner inherits these
    assert "SPOTIFY_CLIENT_ID" not in os.environ
