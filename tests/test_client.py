from __future__ import annotations

import httpx
import pytest
import respx

from spotify_mcp.client import SpotifyClient
from spotify_mcp.config import SPOTIFY_API_BASE
from spotify_mcp.exceptions import SpotifyAPIError


class FakeAuth:
    """Minimal AuthManager stub: hands out tokens, tracks invalidations."""

    def __init__(self, tokens: list[str] | None = None) -> None:
        self._tokens = tokens or ["token-1"]
        self._idx = 0
        self.invalidate_calls = 0

    async def get_access_token(self) -> str:
        token = self._tokens[min(self._idx, len(self._tokens) - 1)]
        return token

    def invalidate(self) -> None:
        self.invalidate_calls += 1
        # Advance to next token to simulate re-auth giving a fresh one.
        self._idx = min(self._idx + 1, len(self._tokens) - 1)


@pytest.fixture
def client() -> SpotifyClient:
    return SpotifyClient(FakeAuth())


@respx.mock
async def test_get_returns_parsed_json(client: SpotifyClient) -> None:
    route = respx.get(f"{SPOTIFY_API_BASE}/tracks/abc").mock(
        return_value=httpx.Response(200, json={"id": "abc", "name": "Song"})
    )
    data = await client.get("/tracks/abc")
    assert data == {"id": "abc", "name": "Song"}
    assert route.called
    sent = route.calls.last.request
    assert sent.headers["Authorization"] == "Bearer token-1"


@respx.mock
async def test_get_strips_none_params(client: SpotifyClient) -> None:
    route = respx.get(f"{SPOTIFY_API_BASE}/search").mock(return_value=httpx.Response(200, json={}))
    await client.get("/search", params={"q": "foo", "market": None, "limit": 10})
    sent = route.calls.last.request
    assert "market" not in sent.url.params
    assert sent.url.params["q"] == "foo"
    assert sent.url.params["limit"] == "10"


@respx.mock
async def test_204_returns_empty_dict(client: SpotifyClient) -> None:
    respx.put(f"{SPOTIFY_API_BASE}/me/player/play").mock(return_value=httpx.Response(204))
    result = await client.put("/me/player/play")
    assert result == {}


@respx.mock
async def test_200_with_empty_body_returns_empty_dict(client: SpotifyClient) -> None:
    respx.post(f"{SPOTIFY_API_BASE}/me/player/queue").mock(
        return_value=httpx.Response(200, content=b"")
    )
    result = await client.post("/me/player/queue")
    assert result == {}


@respx.mock
async def test_401_triggers_invalidate_and_retries() -> None:
    auth = FakeAuth(tokens=["stale", "fresh"])
    client = SpotifyClient(auth)
    route = respx.get(f"{SPOTIFY_API_BASE}/me").mock(
        side_effect=[
            httpx.Response(401, json={"error": {"message": "expired"}}),
            httpx.Response(200, json={"id": "user1"}),
        ]
    )
    data = await client.get("/me")
    assert data == {"id": "user1"}
    assert auth.invalidate_calls == 1
    assert route.call_count == 2
    # Second call must use the refreshed token
    assert route.calls[1].request.headers["Authorization"] == "Bearer fresh"


@respx.mock
async def test_401_only_retries_once(client: SpotifyClient) -> None:
    respx.get(f"{SPOTIFY_API_BASE}/me").mock(
        return_value=httpx.Response(401, json={"error": {"message": "no"}})
    )
    with pytest.raises(SpotifyAPIError) as exc_info:
        await client.get("/me")
    assert exc_info.value.status_code == 401


@respx.mock
async def test_429_uses_retry_after_then_succeeds(
    client: SpotifyClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr("spotify_mcp.client.asyncio.sleep", fake_sleep)

    respx.get(f"{SPOTIFY_API_BASE}/tracks/x").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "3"}),
            httpx.Response(200, json={"id": "x"}),
        ]
    )
    data = await client.get("/tracks/x")
    assert data == {"id": "x"}
    assert sleeps and sleeps[0] >= 3  # Honored Retry-After


@respx.mock
async def test_429_exhausts_retries(client: SpotifyClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_sleep(seconds: float) -> None:
        return None

    monkeypatch.setattr("spotify_mcp.client.asyncio.sleep", fake_sleep)

    respx.get(f"{SPOTIFY_API_BASE}/tracks/x").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "1"})
    )
    with pytest.raises(SpotifyAPIError) as exc_info:
        await client.get("/tracks/x")
    assert exc_info.value.status_code == 429
    # New: retry_after is attached so callers can honor it.
    assert exc_info.value.retry_after == 1


@respx.mock
async def test_403_includes_scope_hint(client: SpotifyClient) -> None:
    respx.get(f"{SPOTIFY_API_BASE}/me/top/tracks").mock(
        return_value=httpx.Response(
            403, json={"error": {"status": 403, "message": "Insufficient scope"}}
        )
    )
    with pytest.raises(SpotifyAPIError) as exc_info:
        await client.get("/me/top/tracks")
    assert exc_info.value.status_code == 403
    assert "scopes" in exc_info.value.message.lower()
    assert "Insufficient scope" in exc_info.value.message


@respx.mock
async def test_404_surfaces_api_message(client: SpotifyClient) -> None:
    respx.get(f"{SPOTIFY_API_BASE}/tracks/missing").mock(
        return_value=httpx.Response(
            404, json={"error": {"status": 404, "message": "non existing id"}}
        )
    )
    with pytest.raises(SpotifyAPIError) as exc_info:
        await client.get("/tracks/missing")
    assert exc_info.value.status_code == 404
    assert exc_info.value.message == "non existing id"


@respx.mock
async def test_error_with_non_json_body(client: SpotifyClient) -> None:
    respx.get(f"{SPOTIFY_API_BASE}/tracks/x").mock(
        return_value=httpx.Response(500, content=b"<html>boom</html>")
    )
    with pytest.raises(SpotifyAPIError) as exc_info:
        await client.get("/tracks/x")
    assert exc_info.value.status_code == 500
    assert "boom" in exc_info.value.message
