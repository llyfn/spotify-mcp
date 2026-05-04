from __future__ import annotations

import asyncio
import sys
from typing import Any

import httpx

from spotify_mcp.auth import AuthManager
from spotify_mcp.config import SPOTIFY_API_BASE
from spotify_mcp.exceptions import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    SpotifyAPIError,
)

MAX_RETRIES = 3


class SpotifyClient:
    """Async Spotify API client with automatic auth, retry, and error handling."""

    def __init__(self, auth: AuthManager) -> None:
        self._auth = auth
        self._http = httpx.AsyncClient(
            base_url=SPOTIFY_API_BASE,
            timeout=30.0,
        )

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self._request("GET", path, params=params)

    async def post(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        return await self._request("POST", path, params=params, json=json)

    async def put(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        return await self._request("PUT", path, params=params, json=json)

    async def delete(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        return await self._request("DELETE", path, params=params, json=json)

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        """Make an authenticated request with retry logic."""
        # Filter out None values from params
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        for attempt in range(MAX_RETRIES + 1):
            token = await self._auth.get_access_token()
            headers = {"Authorization": f"Bearer {token}"}

            response = await self._http.request(
                method,
                path,
                params=params,
                json=json,
                headers=headers,
            )

            # Success - return parsed JSON, empty dict for 204 or non-JSON body
            if response.status_code in (200, 201):
                if not response.content:
                    return {}
                try:
                    return response.json()
                except ValueError:
                    return {}
            if response.status_code == 204:
                return {}

            # 401 Unauthorized - token may have expired mid-request
            if response.status_code == 401 and attempt == 0:
                # Force a token refresh on next get_access_token() call
                self._auth._expires_at = 0
                continue

            # 429 Rate limited - exponential backoff
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "1"))
                wait_time = max(retry_after, 2**attempt)
                if attempt < MAX_RETRIES:
                    print(
                        f"Rate limited. Retrying in {wait_time}s...",
                        file=sys.stderr,
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise RateLimitError(retry_after=retry_after)

            # Map error responses
            error_message = self._extract_error_message(response)

            if response.status_code == 404:
                raise NotFoundError(error_message)
            if response.status_code == 403:
                raise SpotifyAPIError(
                    403,
                    f"Forbidden: {error_message}. Check that your app has the required scopes.",
                )
            raise SpotifyAPIError(response.status_code, error_message)

        raise AuthenticationError("Failed to authenticate after retries")

    @staticmethod
    def _extract_error_message(response: httpx.Response) -> str:
        """Extract a human-readable error message from a Spotify API error response."""
        try:
            data = response.json()
            if "error" in data:
                error = data["error"]
                if isinstance(error, dict):
                    return error.get("message", str(error))
                return str(error)
        except Exception:
            pass
        return response.text or f"HTTP {response.status_code}"

    async def close(self) -> None:
        await self._http.aclose()
