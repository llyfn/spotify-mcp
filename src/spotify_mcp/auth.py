from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import secrets
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from spotify_mcp.config import (
    ALL_SCOPES,
    CREDENTIALS_DIR,
    CREDENTIALS_FILE,
    SPOTIFY_AUTH_URL,
    SPOTIFY_TOKEN_URL,
    get_client_id,
    get_client_secret,
    get_redirect_uri,
)
from spotify_mcp.exceptions import AuthenticationError


class AuthManager:
    """Manages OAuth tokens: loading, refreshing, and running the full auth flow."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at: float = 0

    def invalidate(self) -> None:
        """Mark the current access token as expired so the next request refreshes."""
        self._expires_at = 0

    async def get_access_token(self) -> str:
        """Return a valid access token, refreshing or authenticating as needed."""
        async with self._lock:
            if self._access_token and time.time() < self._expires_at - 60:
                return self._access_token

            # Try loading from disk
            if self._load_credentials():
                if time.time() < self._expires_at - 60:
                    return self._access_token  # type: ignore[return-value]
                # Token expired, try refresh
                if self._refresh_token:
                    try:
                        await self._refresh_access_token()
                        return self._access_token  # type: ignore[return-value]
                    except AuthenticationError:
                        pass  # Fall through to full auth flow

            # Run full OAuth flow
            await self._run_auth_flow()
            return self._access_token  # type: ignore[return-value]

    def _load_credentials(self) -> bool:
        """Load credentials from disk. Returns True if credentials were found."""
        if not CREDENTIALS_FILE.exists():
            return False
        try:
            data = json.loads(CREDENTIALS_FILE.read_text())
            self._access_token = data["access_token"]
            self._refresh_token = data.get("refresh_token")
            self._expires_at = data.get("expires_at", 0)
            return True
        except (json.JSONDecodeError, KeyError):
            return False

    def _save_credentials(self) -> None:
        """Save credentials to disk with secure permissions."""
        CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
        CREDENTIALS_DIR.chmod(0o700)
        data = {
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
            "expires_at": self._expires_at,
        }
        CREDENTIALS_FILE.write_text(json.dumps(data, indent=2))
        CREDENTIALS_FILE.chmod(0o600)

    async def _refresh_access_token(self) -> None:
        """Use the refresh token to get a new access token."""
        client_id = get_client_id()
        client_secret = get_client_secret()
        auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

        async with httpx.AsyncClient() as http:
            response = await http.post(
                SPOTIFY_TOKEN_URL,
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                },
                timeout=30.0,
            )

        if response.status_code != 200:
            raise AuthenticationError(
                f"Token refresh failed: {response.status_code} {response.text}"
            )

        token_data = response.json()
        self._access_token = token_data["access_token"]
        if "refresh_token" in token_data:
            self._refresh_token = token_data["refresh_token"]
        self._expires_at = time.time() + token_data.get("expires_in", 3600)
        self._save_credentials()

    async def _run_auth_flow(self) -> None:
        """Run the full Authorization Code flow with a local callback server."""
        client_id = get_client_id()
        client_secret = get_client_secret()
        redirect_uri = get_redirect_uri()

        parsed = urlparse(redirect_uri)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 8888
        callback_path = parsed.path or "/callback"

        state = secrets.token_urlsafe(32)
        auth_code_future: dict[str, Any] = {"code": None, "error": None}

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parsed_path = urlparse(self.path)
                if parsed_path.path != callback_path:
                    self.send_response(404)
                    self.end_headers()
                    return

                params = parse_qs(parsed_path.query)

                if "error" in params:
                    auth_code_future["error"] = params["error"][0]
                elif "code" in params:
                    received_state = params.get("state", [""])[0]
                    if received_state != state:
                        auth_code_future["error"] = "State mismatch - possible CSRF attack"
                    else:
                        auth_code_future["code"] = params["code"][0]

                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                if auth_code_future["error"]:
                    self.wfile.write(
                        b"<html><body><h1>Authentication Failed</h1>"
                        b"<p>You can close this tab.</p></body></html>"
                    )
                else:
                    self.wfile.write(
                        b"<html><body><h1>Authentication Successful!</h1>"
                        b"<p>You can close this tab and return to your application.</p>"
                        b"</body></html>"
                    )

            def log_message(self, format: str, *args: Any) -> None:
                pass  # Suppress HTTP server logs on stdout

        auth_url = (
            SPOTIFY_AUTH_URL
            + "?"
            + urlencode(
                {
                    "client_id": client_id,
                    "response_type": "code",
                    "redirect_uri": redirect_uri,
                    "scope": ALL_SCOPES,
                    "state": state,
                }
            )
        )

        print(
            "\n=== Spotify Authentication Required ===\n"
            f"Please open this URL in your browser:\n\n{auth_url}\n",
            file=sys.stderr,
        )

        server = HTTPServer((host, port), CallbackHandler)
        server.timeout = 1

        def run_server() -> None:
            while auth_code_future["code"] is None and auth_code_future["error"] is None:
                server.handle_request()

        server_thread = Thread(target=run_server, daemon=True)
        server_thread.start()

        with contextlib.suppress(Exception):
            webbrowser.open(auth_url)

        # Wait for callback with timeout
        deadline = time.time() + 120
        while (
            auth_code_future["code"] is None
            and auth_code_future["error"] is None
            and time.time() < deadline
        ):
            await asyncio.sleep(0.5)

        server.server_close()

        if auth_code_future["error"]:
            raise AuthenticationError(f"Authentication failed: {auth_code_future['error']}")
        if auth_code_future["code"] is None:
            raise AuthenticationError("Authentication timed out. Please try again.")

        # Exchange code for tokens
        auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

        async with httpx.AsyncClient() as http:
            response = await http.post(
                SPOTIFY_TOKEN_URL,
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "authorization_code",
                    "code": auth_code_future["code"],
                    "redirect_uri": redirect_uri,
                },
                timeout=30.0,
            )

        if response.status_code != 200:
            raise AuthenticationError(
                f"Token exchange failed: {response.status_code} {response.text}"
            )

        token_data = response.json()
        self._access_token = token_data["access_token"]
        self._refresh_token = token_data.get("refresh_token")
        self._expires_at = time.time() + token_data.get("expires_in", 3600)
        self._save_credentials()

        print("Authentication successful!", file=sys.stderr)
