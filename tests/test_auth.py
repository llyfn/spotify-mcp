from __future__ import annotations

import json
import time
from pathlib import Path

import httpx
import pytest
import respx

from spotify_mcp import config
from spotify_mcp.auth import AuthManager
from spotify_mcp.exceptions import AuthenticationError


def _write_credentials(path: Path, **overrides: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "access_token": "stored-access",
        "refresh_token": "stored-refresh",
        "expires_at": time.time() + 3600,
    }
    data.update(overrides)
    path.write_text(json.dumps(data))


async def test_uses_cached_token_when_not_expired() -> None:
    _write_credentials(config.CREDENTIALS_FILE)
    auth = AuthManager()
    token = await auth.get_access_token()
    assert token == "stored-access"


async def test_load_credentials_returns_false_when_file_missing() -> None:
    auth = AuthManager()
    assert auth._load_credentials() is False


async def test_load_credentials_returns_false_on_invalid_json() -> None:
    config.CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.CREDENTIALS_FILE.write_text("{not json")
    auth = AuthManager()
    assert auth._load_credentials() is False


async def test_load_credentials_returns_false_on_missing_keys() -> None:
    config.CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.CREDENTIALS_FILE.write_text(json.dumps({"refresh_token": "x"}))
    auth = AuthManager()
    assert auth._load_credentials() is False


async def test_save_credentials_sets_secure_permissions() -> None:
    auth = AuthManager()
    auth._access_token = "a"
    auth._refresh_token = "r"
    auth._expires_at = 9999999999
    auth._save_credentials()
    assert config.CREDENTIALS_FILE.exists()
    # Owner-only perms (mode bits, masked to lowest 9)
    file_mode = config.CREDENTIALS_FILE.stat().st_mode & 0o777
    dir_mode = config.CREDENTIALS_DIR.stat().st_mode & 0o777
    assert file_mode == 0o600
    assert dir_mode == 0o700
    payload = json.loads(config.CREDENTIALS_FILE.read_text())
    assert payload["access_token"] == "a"
    assert payload["refresh_token"] == "r"


@respx.mock
async def test_expired_token_triggers_refresh(spotify_env: None) -> None:
    _write_credentials(config.CREDENTIALS_FILE, expires_at=time.time() - 100)
    respx.post(config.SPOTIFY_TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={"access_token": "refreshed-access", "expires_in": 3600},
        )
    )
    auth = AuthManager()
    token = await auth.get_access_token()
    assert token == "refreshed-access"
    # Refresh token should be retained when not returned in the response
    assert auth._refresh_token == "stored-refresh"
    # Persisted to disk
    payload = json.loads(config.CREDENTIALS_FILE.read_text())
    assert payload["access_token"] == "refreshed-access"


@respx.mock
async def test_refresh_uses_returned_refresh_token_when_provided(spotify_env: None) -> None:
    _write_credentials(config.CREDENTIALS_FILE, expires_at=time.time() - 100)
    respx.post(config.SPOTIFY_TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "refreshed-access",
                "refresh_token": "new-refresh",
                "expires_in": 3600,
            },
        )
    )
    auth = AuthManager()
    await auth.get_access_token()
    assert auth._refresh_token == "new-refresh"


@respx.mock
async def test_refresh_failure_raises_authentication_error(spotify_env: None) -> None:
    auth = AuthManager()
    auth._refresh_token = "bad-refresh"
    respx.post(config.SPOTIFY_TOKEN_URL).mock(
        return_value=httpx.Response(400, text="invalid_grant")
    )
    with pytest.raises(AuthenticationError):
        await auth._refresh_access_token()


async def test_invalidate_resets_expiry() -> None:
    auth = AuthManager()
    auth._access_token = "x"
    auth._expires_at = time.time() + 9999
    auth.invalidate()
    assert auth._expires_at == 0


@respx.mock
async def test_get_access_token_falls_through_to_full_flow_on_refresh_failure(
    spotify_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_credentials(config.CREDENTIALS_FILE, expires_at=time.time() - 100)
    respx.post(config.SPOTIFY_TOKEN_URL).mock(
        return_value=httpx.Response(400, text="invalid_grant")
    )

    called = {"flow": False}

    async def fake_flow(self: AuthManager) -> None:
        called["flow"] = True
        self._access_token = "fresh-from-flow"
        self._expires_at = time.time() + 3600

    monkeypatch.setattr(AuthManager, "_run_auth_flow", fake_flow)

    auth = AuthManager()
    token = await auth.get_access_token()
    assert called["flow"] is True
    assert token == "fresh-from-flow"
