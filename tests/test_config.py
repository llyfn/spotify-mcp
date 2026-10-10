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


def test_validate_http_environment_rejects_missing_token(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert "SPOTIFY_MCP_AUTH_TOKEN is required" in _exit_message(capsys)


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


def test_host_and_port_defaults() -> None:
    assert config.get_mcp_host() == "127.0.0.1"
    assert config.get_mcp_port() == 8000


def test_port_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPOTIFY_MCP_PORT", "9000")
    assert config.get_mcp_port() == 9000


@pytest.mark.parametrize("raw", ["abc", "0", "65536", "-1"])
def test_invalid_port_raises(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    monkeypatch.setenv("SPOTIFY_MCP_PORT", raw)
    with pytest.raises(ValueError):
        config.get_mcp_port()


def test_allowed_hosts_are_split_and_trimmed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPOTIFY_MCP_ALLOWED_HOSTS", " spotify.example.com , 10.0.0.5:*,, ")
    assert config.get_mcp_allowed_hosts() == ["spotify.example.com", "10.0.0.5:*"]


@pytest.mark.parametrize(
    ("host", "expected"),
    [("127.0.0.1", True), ("localhost", True), ("::1", True), ("0.0.0.0", False), ("::", False)],
)
def test_is_loopback_host(host: str, expected: bool) -> None:
    assert config.is_loopback_host(host) is expected


def _exit_message(capsys: pytest.CaptureFixture[str]) -> str:
    with pytest.raises(SystemExit) as exc:
        config.validate_http_environment()
    assert exc.value.code == 1
    return capsys.readouterr().err


def test_validate_rejects_invalid_port(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SPOTIFY_MCP_PORT", "abc")
    assert "SPOTIFY_MCP_PORT" in _exit_message(capsys)


def test_validate_rejects_remote_bind_without_token(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SPOTIFY_MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("SPOTIFY_MCP_ALLOWED_HOSTS", "spotify.example.com")
    assert "SPOTIFY_MCP_AUTH_TOKEN is required" in _exit_message(capsys)


def test_validate_rejects_remote_bind_without_allowed_hosts(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SPOTIFY_MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("SPOTIFY_MCP_AUTH_TOKEN", "t" * 43)
    assert "SPOTIFY_MCP_ALLOWED_HOSTS" in _exit_message(capsys)


def test_validate_accepts_complete_remote_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPOTIFY_MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("SPOTIFY_MCP_AUTH_TOKEN", "t" * 43)
    monkeypatch.setenv("SPOTIFY_MCP_ALLOWED_HOSTS", "spotify.example.com")
    assert config.validate_http_environment() == "t" * 43
