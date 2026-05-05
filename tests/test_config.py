from __future__ import annotations

import pytest

from spotify_mcp import config


def test_get_client_id_reads_env(spotify_env: None) -> None:
    assert config.get_client_id() == "test-client-id"


def test_get_client_secret_reads_env(spotify_env: None) -> None:
    assert config.get_client_secret() == "test-client-secret"


def test_get_redirect_uri_default_when_unset(spotify_env: None) -> None:
    assert config.get_redirect_uri() == config.DEFAULT_REDIRECT_URI


def test_get_redirect_uri_uses_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:9000/cb")
    assert config.get_redirect_uri() == "http://127.0.0.1:9000/cb"


def test_validate_environment_passes_with_required_vars(spotify_env: None) -> None:
    config.validate_environment()  # should not raise or exit


def test_validate_environment_exits_when_missing(
    no_spotify_env: None, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        config.validate_environment()
    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "SPOTIFY_CLIENT_ID" in err
    assert "SPOTIFY_CLIENT_SECRET" in err


def test_all_scopes_includes_required_scopes() -> None:
    # Sanity: feedback memory says request only minimum scopes; core ones must be present.
    for scope in (
        "user-read-private",
        "user-read-playback-state",
        "user-modify-playback-state",
        "playlist-read-private",
        "playlist-modify-private",
    ):
        assert scope in config.ALL_SCOPES
