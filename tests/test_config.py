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


def test_all_scopes_excludes_user_read_email() -> None:
    # GET /me no longer returns email, so the scope grants nothing.
    assert "user-read-email" not in config.ALL_SCOPES.split()


def test_auth_token_is_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPOTIFY_MCP_AUTH_TOKEN", raising=False)
    assert config.get_mcp_auth_token() is None


def test_auth_token_is_none_when_blank(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPOTIFY_MCP_AUTH_TOKEN", "   ")
    assert config.get_mcp_auth_token() is None


def test_auth_token_is_stripped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPOTIFY_MCP_AUTH_TOKEN", "t" * 40 + "\n")
    assert config.get_mcp_auth_token() == "t" * 40


def test_validate_http_environment_passes_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPOTIFY_MCP_AUTH_TOKEN", raising=False)
    config.validate_http_environment()


def test_validate_http_environment_rejects_short_token(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SPOTIFY_MCP_AUTH_TOKEN", "short")
    with pytest.raises(SystemExit) as exc:
        config.validate_http_environment()
    assert exc.value.code == 1
    assert "SPOTIFY_MCP_AUTH_TOKEN" in capsys.readouterr().err


def test_validate_http_environment_rejects_non_ascii_token(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SPOTIFY_MCP_AUTH_TOKEN", "ö" * 40)
    with pytest.raises(SystemExit) as exc:
        config.validate_http_environment()
    assert exc.value.code == 1
    assert "SPOTIFY_MCP_AUTH_TOKEN" in capsys.readouterr().err
