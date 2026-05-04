# Contributing to Spotify MCP Server

Thanks for your interest in contributing! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

### Getting Started

```bash
# Clone the repository
git clone https://github.com/llyfn/spotify-mcp.git
cd spotify-mcp

# Install dependencies (including dev tools)
uv sync --dev

# Run the server locally
uv run spotify-mcp
```

### Code Quality

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy src/
```

## Adding a New Tool

Adding a tool is the most common contribution. Here's how:

### 1. Choose or Create a Tool Module

Tools are organized by category in `src/spotify_mcp/tools/`. Pick the module that fits your tool, or create a new one for a new category.

### 2. Define Your Tool

Each tool module follows this pattern:

```python
# src/spotify_mcp/tools/example.py
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from spotify_mcp.client import SpotifyClient


def register(mcp: FastMCP, client: SpotifyClient) -> None:
    @mcp.tool()
    async def my_new_tool(required_param: str, optional_param: int = 10) -> str:
        """Short description of what this tool does.

        Args:
            required_param: Description of this parameter.
            optional_param: Description with default noted (default 10).
        """
        data = await client.get(f"/endpoint/{required_param}", params={"limit": optional_param})
        # Format the response into a human-readable string
        return f"Result: {data.get('name')}"
```

### 3. Register Your Module

If you created a new module, add it to `src/spotify_mcp/tools/__init__.py`:

```python
from spotify_mcp.tools import (
    # ... existing imports ...
    example,  # Add your new module
)

_MODULES = [
    # ... existing modules ...
    example,  # Add your new module
]
```

### Guidelines for Tools

- **Use non-deprecated endpoints only.** Check the [Spotify OpenAPI spec](https://developer.spotify.com/reference/web-api/open-api-schema.yaml) for deprecation status.
- **Return human-readable strings**, not raw JSON. The LLM needs clean, formatted text.
- **Include Spotify IDs** in output so the LLM can chain tool calls (e.g., search -> get details).
- **Write clear docstrings.** The docstring becomes the tool description that the LLM sees. Keep it concise (1-2 sentences) and include `Args:` with parameter descriptions.
- **Request minimum scopes.** Don't add scopes to `config.py` unless your endpoint actually requires them.
- **Use the `client` methods** (`client.get()`, `client.post()`, etc.) — never use `httpx` directly.
- **Handle pagination** with `limit` and `offset` parameters where applicable.

## Project Structure

```
src/spotify_mcp/
├── __init__.py          # Package entry point
├── __main__.py          # python -m spotify_mcp entry
├── server.py            # FastMCP instance and startup
├── auth.py              # OAuth flow and token management
├── client.py            # HTTP client with retry/error handling
├── config.py            # Configuration and constants
├── exceptions.py        # Exception hierarchy
└── tools/               # Tool modules (one per category)
    ├── __init__.py      # Tool registration hub
    ├── albums.py
    ├── artists.py
    └── ...
```

### Key Architecture Decisions

- **Closure-based tools**: Tools are defined inside `register()` functions, giving them access to the `client` without globals.
- **Single HTTP bottleneck**: All API calls go through `SpotifyClient._request()`, which handles auth headers, token refresh, rate limiting, and error mapping.
- **Token persistence**: OAuth tokens are stored in `~/.spotify-mcp/credentials.json` so they survive server restarts.

## Submitting Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run lint and format: `uv run ruff check . && uv run ruff format .`
5. Commit with a clear message
6. Push and open a pull request

## Reporting Issues

Please [open an issue](https://github.com/llyfn/spotify-mcp/issues) with:

- Steps to reproduce
- Expected vs. actual behavior
- Python version and OS
- Relevant error messages or logs

## For AI Agents

If you are an AI agent contributing to this project, follow these rules when working with the Spotify Web API:

- **OpenAPI spec**: Refer to the [Spotify OpenAPI specification](https://developer.spotify.com/reference/web-api/open-api-schema.yaml) for all endpoint paths, parameters, and response schemas. Do not guess endpoints or field names.
- **Authorization**: Use the [Authorization Code with PKCE flow](https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow) for any user-specific data. If the app has a secure backend, the [Authorization Code flow](https://developer.spotify.com/documentation/web-api/tutorials/code-flow) is also acceptable. Only use Client Credentials for public, non-user data. Never use the Implicit Grant flow (it is deprecated).
- **Redirect URIs**: Always use HTTPS redirect URIs (except `http://127.0.0.1` for local development). Never use `http://localhost` or wildcard URIs. See [redirect URI requirements](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri).
- **Scopes**: Request only the minimum [scopes](https://developer.spotify.com/documentation/web-api/concepts/scopes) needed for the features being built. Do not request broad scopes preemptively.
- **Token management**: Store tokens securely. Never expose the Client Secret in client-side code. Implement [token refresh](https://developer.spotify.com/documentation/web-api/tutorials/refreshing-tokens) logic so the app does not break when access tokens expire.
- **Rate limits**: Implement exponential backoff and respect the `Retry-After` header when receiving HTTP 429 responses. Do not retry immediately or in tight loops.
- **Deprecated endpoints**: Do not use deprecated endpoints. Prefer `/playlists/{id}/items` over `/playlists/{id}/tracks`, and use `/me/library` over the type-specific library endpoints.
- **Error handling**: Handle all HTTP error codes documented in the OpenAPI schema. Read the returned error message and use it to provide meaningful feedback to the user.
- **Developer Terms of Service**: Comply with the [Spotify Developer Terms](https://developer.spotify.com/terms). In particular: do not cache Spotify content beyond what is needed for immediate use, always attribute content to Spotify, and do not use the API to train machine learning models on Spotify data.
