# Spotify Web API 2026 Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring every tool, resource, and scope in `mcp-server-spotify` in line with the Spotify Web API as of September 2026, and release it as 0.3.0.

**Architecture:** No structural change. Tools that call removed endpoints are deleted, not emulated. Follow/unfollow moves onto the existing `/me/library` tools, which take URIs. Formatters stop reading removed response fields. `client.py` adds a clearer message for the new `QUOTA_EXCEEDED` 429 reason.

**Tech Stack:** Python 3.12, FastMCP (`mcp[cli]`), httpx, pytest + pytest-asyncio + respx, ruff, uv.

**Spec (source of truth, read before starting):**
- OpenAPI schema: https://developer.spotify.com/reference/web-api/open-api-schema.yaml
- Changelogs: [Feb 2026](https://developer.spotify.com/documentation/web-api/references/changes/february-2026), [Mar 2026](https://developer.spotify.com/documentation/web-api/references/changes/march-2026), [May 2026](https://developer.spotify.com/documentation/web-api/references/changes/may-2026), [Jul 2026](https://developer.spotify.com/documentation/web-api/references/changes/july-2026)
- [February 2026 migration guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide)
- `CONTRIBUTING.md` → Spotify Web API rules

## Global Constraints

- Never call an endpoint the OpenAPI spec marks `deprecated: true`.
- `PUT /me/library`, `DELETE /me/library`, `GET /me/library/contains`: **max 40 URIs per request** (spec: "Maximum: 40 URIs").
- `GET /search` `limit`: min 0, max 10, API default 5.
- Removed fields (do not read or display): Album `album_group`, `available_markets`, `label`, `popularity`; Artist `followers`, `popularity`; Audiobook `available_markets`, `publisher`; Chapter `available_markets`; Show `available_markets`, `publisher`; Track `available_markets`, `linked_from`, `popularity`; User `country`, `email`, `explicit_content`, `followers`, `product`; Playlist `followers`.
- Kept fields: Album and Track `external_ids` (restored in the Mar 2026 changelog).
- Playlist objects: use `items` (not the deprecated `tracks`). Playlist entries: use `item` (not the deprecated `track`).
- Request the minimum scopes. Don't add scopes.
- Commit messages: Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`), matching the repo history. **No `Co-Authored-By` trailer and no "Generated with Claude Code" line.**
- Verification commands: `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .`. Baseline before Task 1: 76 passed, ruff clean.
- Work on the branch `chore/spotify-api-2026-migration`, created from `main`.

## File Map

| File | Change |
|---|---|
| `src/spotify_mcp/tools/library.py` | Chunk size 50 → 40. Docstrings list artist/user/playlist URIs. |
| `src/spotify_mcp/tools/following.py` | Delete 5 tools. Keep `get_followed_artists`. |
| `src/spotify_mcp/tools/{albums,artists,tracks,shows,audiobooks}.py` | Delete the 7 batch tools and their `_*_MAX_IDS` constants. Stop reading removed fields. |
| `src/spotify_mcp/tools/playlists.py` | `tracks` → `items`, `track` → `item`. Drop `followers`. |
| `src/spotify_mcp/tools/search.py` | Stop reading artist `followers` and show `publisher`. Fix the `limit` docstring. |
| `src/spotify_mcp/tools/users.py`, `src/spotify_mcp/resources.py` | Show `account_id`. Drop removed user fields. |
| `src/spotify_mcp/config.py` | Drop the `user-read-email` scope. |
| `src/spotify_mcp/client.py` | Clearer error message for 429 `QUOTA_EXCEEDED`. |
| `tests/test_tools_behavior.py`, `tests/test_tools_registration.py`, `tests/test_client.py`, `tests/test_config.py` | Update/add tests per task. |
| `README.md`, `pyproject.toml` | Tool tables, feature list, version 0.3.0. |

---

### Task 1: Verify two spec ambiguities against the live API (manual, no commit)

The migration guide says `PUT/DELETE /me/library` accept `spotify:artist:` URIs. The OpenAPI spec's list of supported URI types for PUT/DELETE leaves out `artist`; only `/contains` lists it. Task 2's docstrings depend on the answer.

This task **temporarily follows an artist on the operator's real account and then restores the original state.** Get the user's go-ahead before running it.

**Files:** none committed. The script goes in the session scratchpad.

- [ ] **Step 1: Create the branch**

```bash
git checkout -b chore/spotify-api-2026-migration
```

- [ ] **Step 2: Write the probe script** to `<scratchpad>/probe_library.py`

```python
import asyncio

from spotify_mcp.auth import AuthManager
from spotify_mcp.client import SpotifyClient
from spotify_mcp.exceptions import SpotifyAPIError

ARTIST = "spotify:artist:4Z8W4fKeB5YxbusRsdQVPb"  # Radiohead


async def main() -> None:
    client = SpotifyClient(AuthManager())
    try:
        (before,) = await client.get("/me/library/contains", params={"uris": ARTIST})
        print("contains before:", before)
        try:
            await client.put("/me/library", params={"uris": ARTIST})
            print("PUT artist: OK")
        except SpotifyAPIError as e:
            print("PUT artist FAILED:", e.status_code, e.message)
            return
        (after,) = await client.get("/me/library/contains", params={"uris": ARTIST})
        print("contains after PUT:", after)
        if not before:
            try:
                await client.delete("/me/library", params={"uris": ARTIST})
                print("DELETE artist: OK")
            except SpotifyAPIError as e:
                print("DELETE artist FAILED:", e.status_code, e.message)
        me = await client.get("/me")
        print("GET /me keys:", sorted(me))
    finally:
        await client.aclose()


asyncio.run(main())
```

- [ ] **Step 3: Run it**

Run: `uv run python <scratchpad>/probe_library.py` (needs `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` and stored credentials).

- [ ] **Step 4: Record the outcome in this plan file** under "Task 1 results" below, then apply this rule:
  - `PUT artist: OK` and `contains after PUT: True` → **ARTIST_SUPPORTED = yes**. Task 2 docstrings list `artist` for save/remove.
  - `PUT artist FAILED` (400) → **ARTIST_SUPPORTED = no**. Task 2 docstrings list `artist` only for `check_saved_in_library`. Task 9 README says the API does not support following artists for this app.
  - If `DELETE artist FAILED` after a successful PUT, tell the user so they can unfollow manually.
  - Confirm that `GET /me keys` includes `account_id` (Task 7 depends on it).

**Task 1 results (2026-09-26, run via the session's installed spotify MCP server, v0.2.0):**
- **ARTIST_SUPPORTED = yes.** `PUT /me/library` and `DELETE /me/library` with `spotify:artist:4Z8W4fKeB5YxbusRsdQVPb` both succeeded, `contains` reflected each change, and the account was restored to following.
- `GET /tracks?ids=...` (batch) → 403 for this app, which confirms the removal.
- `GET /artists/{id}` returned no `followers`, `popularity`, or `genres`.
- `GET /me` still returns `email`, `country`, `product`, `followers` for this app, although the spec marks them deprecated. `account_id` presence: not observable through the v0.2.0 formatter.

---

### Task 2: Library tools: 40-URI chunks and follow-capable URIs

**Files:**
- Modify: `src/spotify_mcp/tools/library.py` (constant at line 13; docstrings of `save_to_library`, `remove_from_library`, `check_saved_in_library`)
- Test: `tests/test_tools_behavior.py` (replace `test_save_to_library_chunks_at_50` and `test_check_saved_in_library_merges_chunked_results`)

**Interfaces:**
- Produces: `save_to_library(uris)`, `remove_from_library(uris)`, `check_saved_in_library(uris)`. Names unchanged; they now also cover follow/unfollow. Task 3 relies on this.

- [ ] **Step 1: Replace the two existing library tests with 40-chunk versions**

In `tests/test_tools_behavior.py`, replace `test_save_to_library_chunks_at_50` with:

```python
async def test_save_to_library_chunks_at_40(mcp_setup: tuple[FastMCP, StubClient]) -> None:
    mcp, client = mcp_setup
    uris = [f"spotify:track:t{i}" for i in range(100)]
    await mcp.call_tool("save_to_library", {"uris": uris})

    puts = [c for c in client.calls if c[0] == "PUT" and c[1] == "/me/library"]
    assert len(puts) == 3
    assert len(puts[0][2]["uris"].split(",")) == 40
    assert len(puts[2][2]["uris"].split(",")) == 20
```

Replace `test_check_saved_in_library_merges_chunked_results` with:

```python
async def test_check_saved_in_library_merges_chunked_results() -> None:
    mcp = FastMCP("test")

    def respond(call_idx: int) -> list[bool]:
        return [True] * 40 if call_idx == 0 else [False] * 20

    client = StubClient(responses={("GET", "/me/library/contains"): respond})
    register_all_tools(mcp, client)  # type: ignore[arg-type]

    uris = [f"spotify:track:t{i}" for i in range(60)]
    result = await mcp.call_tool("check_saved_in_library", {"uris": uris})
    text = _flatten(result)
    assert text.count(": saved") == 40
    assert text.count(": not saved") == 20
```

Add a test that follow-type URIs go through unchanged:

```python
async def test_remove_from_library_unfollows_playlist_by_uri(
    mcp_setup: tuple[FastMCP, StubClient],
) -> None:
    mcp, client = mcp_setup
    await mcp.call_tool(
        "remove_from_library",
        {"uris": ["spotify:playlist:PL", "spotify:user:alice"]},
    )
    method, path, params, _ = client.calls[0]
    assert (method, path) == ("DELETE", "/me/library")
    assert params == {"uris": "spotify:playlist:PL,spotify:user:alice"}
```

- [ ] **Step 2: Run the tests and confirm the chunk tests fail**

Run: `uv run pytest tests/test_tools_behavior.py -k "library" -v`
Expected: `test_save_to_library_chunks_at_40` FAILS (current code sends 2 PUTs of 50). `test_check_saved_in_library_merges_chunked_results` FAILS. The playlist-URI test passes already; it pins behaviour.

- [ ] **Step 3: Implement**

In `library.py`, change line 13:

```python
_LIBRARY_MAX_PER_REQUEST = 40
```

Replace the three docstrings. With **ARTIST_SUPPORTED = yes**:

```python
        """Save items to the user's library, or follow artists, users, and playlists.

        Auto-chunks at 40 URIs per request.

        Args:
            uris: Spotify URIs: track, album, episode, show, audiobook, artist, user, or
                playlist (e.g. ["spotify:track:xxx", "spotify:artist:yyy"]).
        """
```

```python
        """Remove items from the user's library, or unfollow artists, users, and playlists.

        Auto-chunks at 40 URIs per request.

        Args:
            uris: Spotify URIs: track, album, episode, show, audiobook, artist, user, or
                playlist (e.g. ["spotify:track:xxx", "spotify:playlist:yyy"]).
        """
```

```python
        """Check whether items are saved in the user's library, or artists/users/playlists
        are followed.

        Auto-chunks at 40 URIs per request.

        Args:
            uris: Spotify URIs: track, album, episode, show, audiobook, artist, user, or
                playlist (e.g. ["spotify:track:xxx", "spotify:artist:yyy"]).
        """
```

With **ARTIST_SUPPORTED = no**: in the save/remove docstrings, drop "artists" from the first line and `artist` from the URI list. Leave `check_saved_in_library` as above.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_tools_behavior.py -k "library" -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/spotify_mcp/tools/library.py tests/test_tools_behavior.py
git commit -m "fix: chunk library requests at the 40-URI API limit"
```

---

### Task 3: Remove follow tools that call removed endpoints

`PUT/DELETE /me/following`, `GET /me/following/contains`, and `PUT/DELETE /playlists/{id}/followers` are deprecated in the spec. `GET /me/following` is **not** deprecated, so `get_followed_artists` stays.

**Files:**
- Modify: `src/spotify_mcp/tools/following.py`
- Test: `tests/test_tools_registration.py`, `tests/test_tools_behavior.py`

**Interfaces:**
- Consumes: the Task 2 library tools, which replace these.
- Produces: `following.register` registers only `get_followed_artists`.

- [ ] **Step 1: Write the failing registration test**

Add to `tests/test_tools_registration.py`:

```python
REMOVED_TOOLS = {
    "follow_artists_or_users",
    "unfollow_artists_or_users",
    "check_following",
    "follow_playlist",
    "unfollow_playlist",
}


async def test_tools_backed_by_removed_endpoints_are_not_registered(
    mcp_with_tools: tuple[FastMCP, StubClient],
) -> None:
    mcp, _ = mcp_with_tools
    names = {t.name for t in await mcp.list_tools()}
    assert not (REMOVED_TOOLS & names)
```

In `test_register_all_tools_registers_expected_tools`, delete these entries from `expected`: `"follow_artists_or_users"`, `"unfollow_artists_or_users"`, `"check_following"`, `"follow_playlist"`, `"unfollow_playlist"`.

- [ ] **Step 2: Run the test and confirm it fails**

Run: `uv run pytest tests/test_tools_registration.py -v`
Expected: `test_tools_backed_by_removed_endpoints_are_not_registered` FAILS.

- [ ] **Step 3: Implement**

Replace `src/spotify_mcp/tools/following.py` with:

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from spotify_mcp.client import SpotifyClient


def register(mcp: FastMCP, client: SpotifyClient) -> None:
    @mcp.tool()
    async def get_followed_artists(limit: int = 20, after: str | None = None) -> str:
        """Get the current user's followed artists. Cursor-paginated.

        To follow or unfollow, use `save_to_library` / `remove_from_library` with Spotify URIs.

        Args:
            limit: Maximum number of artists to return (1-50, default 20).
            after: Cursor (last artist ID from previous page) to fetch the next page.
        """
        params: dict = {"type": "artist", "limit": limit}
        if after:
            params["after"] = after
        data = await client.get("/me/following", params=params)
        artists_page = data.get("artists", {}) or {}
        items = artists_page.get("items", []) or []
        total = artists_page.get("total")
        lines = []
        for a in items:
            genres = ", ".join(a.get("genres", [])[:3]) or "N/A"
            lines.append(f"- {a.get('name')} ({genres}) (ID: {a.get('id')})")
        cursors = artists_page.get("cursors") or {}
        header = f"Followed artists ({len(items)}"
        if total is not None:
            header += f" of {total}"
        header += "):"
        body = "\n".join(lines) if lines else "  (none)"
        footer = ""
        if cursors.get("after"):
            footer = f"\n\nNext cursor (pass as `after`): {cursors['after']}"
        return f"{header}\n{body}{footer}"
```

In `tests/test_tools_behavior.py`, delete these tests (their tools no longer exist): `test_follow_artists_calls_correct_endpoint`, `test_unfollow_users_chunks_at_50`, `test_follow_validates_type`, `test_check_following_merges_chunks`, `test_follow_playlist_sends_public_in_body`. Keep `test_get_followed_artists_passes_cursor`. In the module docstring, change `- follow/unfollow flow` to `- followed-artists cursor`.

- [ ] **Step 4: Run the tests and lint**

Run: `uv run pytest -q && uv run ruff check .`
Expected: all PASS, ruff clean. `chunked` is still imported by `library.py` and `playlists.py`, so `_utils.chunked` stays.

- [ ] **Step 5: Commit**

```bash
git add src/spotify_mcp/tools/following.py tests/test_tools_registration.py tests/test_tools_behavior.py
git commit -m "refactor!: route follow/unfollow through library tools

The /me/following write endpoints, /me/following/contains, and
/playlists/{id}/followers were removed in the February 2026 Web API
changes. save_to_library, remove_from_library, and check_saved_in_library
accept artist, user, and playlist URIs and replace the removed tools."
```

---

### Task 4: Remove batch lookup tools

`GET /albums`, `/artists`, `/tracks`, `/shows`, `/episodes`, `/audiobooks`, and `/chapters` are deprecated. The single-item tools stay.

**Files:**
- Modify: `src/spotify_mcp/tools/albums.py` (delete `_ALBUMS_MAX_IDS` and `get_albums`)
- Modify: `src/spotify_mcp/tools/artists.py` (delete `_ARTISTS_MAX_IDS` and `get_artists`)
- Modify: `src/spotify_mcp/tools/tracks.py` (delete `_TRACKS_MAX_IDS` and `get_tracks`)
- Modify: `src/spotify_mcp/tools/shows.py` (delete `_SHOWS_MAX_IDS`, `_EPISODES_MAX_IDS`, `get_shows`, and `get_episodes`)
- Modify: `src/spotify_mcp/tools/audiobooks.py` (delete `_AUDIOBOOKS_MAX_IDS`, `_CHAPTERS_MAX_IDS`, `get_audiobooks`, and `get_chapters`)
- Test: `tests/test_tools_registration.py`, `tests/test_tools_behavior.py`

- [ ] **Step 1: Extend the removed-tools test**

In `tests/test_tools_registration.py`, add these to `REMOVED_TOOLS`:

```python
    "get_albums",
    "get_artists",
    "get_tracks",
    "get_shows",
    "get_episodes",
    "get_audiobooks",
    "get_chapters",
```

In `test_register_all_tools_registers_expected_tools`, delete `"get_tracks"`, `"get_albums"`, `"get_artists"`, and `"get_chapters"` from `expected`. Add `"get_chapter"` so the audiobooks module is still spot-checked.

- [ ] **Step 2: Run the test and confirm it fails**

Run: `uv run pytest tests/test_tools_registration.py -v`
Expected: `test_tools_backed_by_removed_endpoints_are_not_registered` FAILS.

- [ ] **Step 3: Implement**

Delete each listed `@mcp.tool()` function in full (decorator through `return`) plus its `_*_MAX_IDS` constants. Each function's body calls `client.get("/<type>s", ...)`; that's how to find it. Keep the blank-line spacing between the remaining functions consistent with the file.

In `tests/test_tools_behavior.py`, delete the `# ---------------- batch lookups ----------------` section: `test_get_tracks_batches_via_ids_param`, `test_get_albums_rejects_over_limit`, `test_get_artists_handles_missing_entries`. In the module docstring, delete the line `- batch lookups`.

- [ ] **Step 4: Run the tests and lint (lint catches imports the deletion left unused)**

Run: `uv run pytest -q && uv run ruff check .`
Expected: all PASS, ruff clean. If ruff reports an unused import (F401) in a touched file, remove that import and rerun.

- [ ] **Step 5: Commit**

```bash
git add src/spotify_mcp/tools tests
git commit -m "refactor!: remove batch lookup tools backed by removed endpoints

The Get Several Albums/Artists/Tracks/Shows/Episodes/Audiobooks/Chapters
endpoints were removed in the February 2026 Web API changes. Use the
single-item tools instead."
```

---

### Task 5: Playlist response fields: `items`/`item`, no `followers`

**Files:**
- Modify: `src/spotify_mcp/tools/playlists.py` (`get_playlist` lines ~29-55, `get_playlist_items` line ~106, `get_my_playlists` line ~192)
- Test: `tests/test_tools_behavior.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_tools_behavior.py` (new section `# ---------------- playlist fields ----------------`):

```python
async def test_get_playlist_reads_items_not_deprecated_tracks() -> None:
    mcp = FastMCP("test")
    client = StubClient(
        responses={
            ("GET", "/playlists/PL"): {
                "name": "Mine",
                "owner": {"display_name": "Alice"},
                "public": True,
                "items": {
                    "total": 1,
                    "items": [{"item": {"name": "Song", "artists": [{"name": "A"}]}}],
                },
            }
        }
    )
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = _flatten(await mcp.call_tool("get_playlist", {"playlist_id": "PL"}))
    assert "Total Tracks: 1" in text
    assert "1. Song - A" in text
    assert "Followers" not in text


async def test_get_playlist_without_items_says_items_unavailable() -> None:
    mcp = FastMCP("test")
    client = StubClient(
        responses={("GET", "/playlists/PL"): {"name": "Theirs", "owner": {"display_name": "Bob"}}}
    )
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = _flatten(await mcp.call_tool("get_playlist", {"playlist_id": "PL"}))
    assert "Items: not available" in text
    assert "Total Tracks" not in text


async def test_get_playlist_items_reads_item_not_deprecated_track() -> None:
    mcp = FastMCP("test")
    client = StubClient(
        responses={
            ("GET", "/playlists/PL/items"): {
                "total": 1,
                "items": [
                    {"item": {"name": "Song", "artists": [{"name": "A"}]}, "added_by": {"id": "u"}}
                ],
            }
        }
    )
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = _flatten(await mcp.call_tool("get_playlist_items", {"playlist_id": "PL"}))
    assert "1. Song - A (added by: u)" in text


async def test_get_my_playlists_counts_from_items_ref() -> None:
    mcp = FastMCP("test")
    client = StubClient(
        responses={
            ("GET", "/me/playlists"): {
                "total": 1,
                "items": [
                    {"id": "PL", "name": "Mine", "owner": {"display_name": "A"}, "items": {"total": 7}}
                ],
            }
        }
    )
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = _flatten(await mcp.call_tool("get_my_playlists", {}))
    assert "(7 tracks, by A)" in text
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_tools_behavior.py -k "playlist" -v`
Expected: the four new tests FAIL.

- [ ] **Step 3: Implement**

In `get_playlist`, replace the body from `owner = ...` to `return result` with:

```python
        owner = data.get("owner", {}).get("display_name", "Unknown")
        items_paged = data.get("items")
        total = (items_paged or {}).get("total", 0)
        items = (items_paged or {}).get("items", [])
        track_lines = []
        for i, entry in enumerate(items[:20], start=1):
            item = entry.get("item")
            if item:
                artists = ", ".join(a["name"] for a in item.get("artists", []))
                track_lines.append(f"  {i}. {item['name']} - {artists}")
        lines = [
            f"Playlist: {data.get('name')}",
            f"Owner: {owner}",
            f"Description: {data.get('description', 'N/A')}",
            f"Public: {data.get('public')}",
        ]
        # Spotify returns `items` only for playlists the user owns or collaborates on.
        if items_paged is None:
            lines.append("Items: not available for playlists you don't own or collaborate on")
        else:
            lines.append(f"Total Tracks: {total}")
        lines.append(f"URL: {data.get('external_urls', {}).get('spotify', 'N/A')}")
        result = "\n".join(lines)
        if track_lines:
            shown = min(20, len(items))
            result += f"\n\nTracks (first {shown} of {total}):\n" + "\n".join(track_lines)
        return result
```

In `get_playlist_items`, change `item = entry.get("track")` to `item = entry.get("item")`.

In `get_my_playlists`, change `count = p.get("tracks", {}).get("total", 0)` to `count = p.get("items", {}).get("total", 0)`.

Then run `grep -n '"track"' tests/test_tools_behavior.py tests/test_tools_registration.py`. Any existing playlist test stub that still uses a `"track"` entry key or a `"tracks"` playlist key must switch to `"item"` / `"items"`.

- [ ] **Step 4: Run the tests and lint**

Run: `uv run pytest -q && uv run ruff check .`
Expected: all PASS, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/spotify_mcp/tools/playlists.py tests/test_tools_behavior.py
git commit -m "fix: read playlist items/item instead of deprecated tracks/track"
```

---

### Task 6: Stop displaying removed catalog fields; fix the search limit docstring

**Files:**
- Modify: `src/spotify_mcp/tools/tracks.py` (`popularity` in `get_track`)
- Modify: `src/spotify_mcp/tools/albums.py` (`popularity` in `get_album`)
- Modify: `src/spotify_mcp/tools/artists.py` (`followers`, `popularity` in `get_artist`)
- Modify: `src/spotify_mcp/tools/shows.py` (`publisher` in `get_show`, `get_episode`)
- Modify: `src/spotify_mcp/tools/audiobooks.py` (`publisher` in `get_audiobook`)
- Modify: `src/spotify_mcp/tools/library.py` (`publisher` in `get_saved_shows`)
- Modify: `src/spotify_mcp/tools/search.py` (artist `followers`, show `publisher`, `limit` docstring)
- Test: `tests/test_tools_behavior.py`, `tests/test_tools_registration.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_tools_behavior.py` (new section `# ---------------- removed fields ----------------`):

```python
async def test_search_artists_does_not_show_follower_count() -> None:
    mcp = FastMCP("test")
    client = StubClient(
        responses={
            ("GET", "/search"): {
                "artists": {"total": 1, "items": [{"id": "a1", "name": "Radiohead"}]}
            }
        }
    )
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = _flatten(await mcp.call_tool("search", {"query": "x", "types": "artist"}))
    assert "Radiohead (ID: a1)" in text
    assert "followers" not in text


async def test_get_episode_does_not_show_publisher_placeholder() -> None:
    mcp = FastMCP("test")
    client = StubClient(
        responses={("GET", "/episodes/e1"): {"name": "Ep", "show": {"name": "Pod"}}}
    )
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = _flatten(await mcp.call_tool("get_episode", {"episode_id": "e1"}))
    assert "Show: Pod" in text
    assert "Unknown" not in text


async def test_get_audiobook_does_not_show_publisher() -> None:
    mcp = FastMCP("test")
    client = StubClient(responses={("GET", "/audiobooks/b1"): {"name": "Book"}})
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = _flatten(await mcp.call_tool("get_audiobook", {"audiobook_id": "b1"}))
    assert "Publisher" not in text


async def test_get_saved_shows_does_not_show_publisher_placeholder() -> None:
    mcp = FastMCP("test")
    client = StubClient(
        responses={
            ("GET", "/me/shows"): {"total": 1, "items": [{"show": {"id": "s1", "name": "Pod"}}]}
        }
    )
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = _flatten(await mcp.call_tool("get_saved_shows", {}))
    assert "- Pod (ID: s1)" in text
```

In `tests/test_tools_registration.py`, `test_get_track_tool_formats_response`: delete the `"popularity": 90,` stub line and the `assert "Popularity: 90" in text` line.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_tools_behavior.py -k "follower or publisher" -v`
Expected: the four new tests FAIL.

- [ ] **Step 3: Implement**

`tracks.py` `get_track`: delete

```python
        if data.get("popularity") is not None:
            lines.append(f"Popularity: {data['popularity']}")
```

`albums.py` `get_album`: delete the same two `popularity` lines.

`artists.py` `get_artist`: delete

```python
        if data.get("followers"):
            lines.append(f"Followers: {data['followers'].get('total', 0):,}")
        if data.get("popularity") is not None:
            lines.append(f"Popularity: {data['popularity']}")
```

`shows.py` `get_show`: delete

```python
        if data.get("publisher"):
            lines.append(f"Publisher: {data['publisher']}")
```

`shows.py` `get_episode`: change

```python
            f"Show: {show.get('name', 'N/A')} (by {show.get('publisher', 'Unknown')})",
```

to

```python
            f"Show: {show.get('name', 'N/A')}",
```

`audiobooks.py` `get_audiobook`: delete the line `f"Publisher: {data.get('publisher', 'Unknown')}\n"`.

`library.py` `get_saved_shows`: replace the `lines.append(...)` call with

```python
            lines.append(f"- {show.get('name')} (ID: {show.get('id')})")
```

`search.py` artists block: replace the two loop-body lines with

```python
                    lines.append(f"  - {a['name']} (ID: {a['id']})")
```

`search.py` shows block: replace the list comprehension line with

```python
                    f"  - {s['name']} (ID: {s['id']})"
```

`search.py` docstring: change `limit: Maximum results per type (1-50, default 10).` to `limit: Maximum results per type (1-10, default 10).`

Check: `grep -rn "popularity\|publisher\|followers" src/spotify_mcp/tools` should now match only `following.py` / `get_followed_artists` (the `/me/following` path), or nothing else.

- [ ] **Step 4: Run the tests and lint**

Run: `uv run pytest -q && uv run ruff check .`
Expected: all PASS, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/spotify_mcp/tools tests
git commit -m "fix: stop displaying catalog fields removed from the Web API

popularity, artist followers, and show/audiobook publisher are no longer
returned. Also document the search limit maximum of 10."
```

---

### Task 7: User profile: `account_id`, drop removed fields and the `user-read-email` scope

`email` was the only reason for `user-read-email`. `user-read-private` stays because the spec still lists it on `GET /me`.

**Files:**
- Modify: `src/spotify_mcp/tools/users.py` (`get_my_profile`, `whoami`)
- Modify: `src/spotify_mcp/resources.py` (`me_profile`)
- Modify: `src/spotify_mcp/config.py` (`ALL_SCOPES`)
- Test: `tests/test_tools_behavior.py`, `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_tools_behavior.py` (new section `# ---------------- profile ----------------`):

```python
_PROFILE = {
    "display_name": "Alice",
    "id": "alice",
    "account_id": "aB3dE5fG7h",
    "external_urls": {"spotify": "https://open.spotify.com/user/alice"},
}


async def test_get_my_profile_shows_account_id_and_no_removed_fields() -> None:
    mcp = FastMCP("test")
    client = StubClient(responses={("GET", "/me"): _PROFILE})
    register_all_tools(mcp, client)  # type: ignore[arg-type]
    text = _flatten(await mcp.call_tool("get_my_profile", {}))
    assert "Account ID: aB3dE5fG7h" in text
    for removed in ("Email", "Country", "Product", "Followers"):
        assert removed not in text


async def test_profile_resource_shows_account_id() -> None:
    from spotify_mcp import resources as resources_mod

    mcp = FastMCP("test")
    client = StubClient(responses={("GET", "/me"): _PROFILE})
    resources_mod.register(mcp, client)  # type: ignore[arg-type]
    contents = await mcp.read_resource("spotify://me/profile")
    text = "\n".join(getattr(c, "content", str(c)) for c in contents)
    assert "Account ID: aB3dE5fG7h" in text
    assert "Plan" not in text
```

In `test_whoami_includes_profile_and_scopes`, change the `/me` stub to `{"display_name": "Alice", "id": "alice", "account_id": "aB3"}` and add:

```python
    assert "Account ID: aB3" in text
    assert "Country" not in text
```

Add to `tests/test_config.py`:

```python
def test_all_scopes_excludes_user_read_email() -> None:
    # GET /me no longer returns email, so the scope grants nothing.
    assert "user-read-email" not in config.ALL_SCOPES.split()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_tools_behavior.py tests/test_config.py -k "profile or whoami or email" -v`
Expected: the new/changed tests FAIL. If `mcp.read_resource` returns a different content type in the installed `mcp` version, adjust only the `text = ...` line so it extracts the string, and keep the assertions.

- [ ] **Step 3: Implement**

`users.py` `get_my_profile`: replace the `return (...)` with

```python
        return (
            f"User: {data.get('display_name', 'N/A')}\n"
            f"ID: {data.get('id')}\n"
            f"Account ID: {data.get('account_id', 'N/A')}\n"
            f"URL: {data.get('external_urls', {}).get('spotify', 'N/A')}"
        )
```

`users.py` `whoami`: replace

```python
            lines.append(f"Country: {profile.get('country', 'N/A')}")
            lines.append(f"Plan: {profile.get('product', 'N/A')}")
```

with

```python
            lines.append(f"Account ID: {profile.get('account_id', 'N/A')}")
```

`resources.py` `me_profile`: replace the `return (...)` with

```python
        return (
            f"User: {data.get('display_name', 'N/A')}\n"
            f"ID: {data.get('id')}\n"
            f"Account ID: {data.get('account_id', 'N/A')}"
        )
```

`config.py`: delete the line `"user-read-email",` from `ALL_SCOPES`.

- [ ] **Step 4: Run the tests and lint**

Run: `uv run pytest -q && uv run ruff check .`
Expected: all PASS, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/spotify_mcp/tools/users.py src/spotify_mcp/resources.py src/spotify_mcp/config.py tests
git commit -m "feat: show account_id in profile; drop removed user fields and email scope"
```

---

### Task 8: Clearer error for 429 `QUOTA_EXCEEDED`

Since July 2026, dev-mode 429 responses can carry `{"error": {"status": 429, "message": "...", "reason": "QUOTA_EXCEEDED"}}`, and the quota is shared across all Client IDs on the developer account. Spotify doesn't document whether retrying helps, so retry behaviour stays as it is. Only the final error message changes.

**Files:**
- Modify: `src/spotify_mcp/client.py` (429 branch, lines ~93-107, plus a new static helper beside `_extract_error_message`)
- Test: `tests/test_client.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_client.py` after `test_429_exhausts_retries`:

```python
@respx.mock
async def test_429_quota_exceeded_explains_shared_quota(
    client: SpotifyClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_sleep(seconds: float) -> None:
        return None

    monkeypatch.setattr("spotify_mcp.client.asyncio.sleep", fake_sleep)

    respx.get(f"{SPOTIFY_API_BASE}/tracks/x").mock(
        return_value=httpx.Response(
            429,
            headers={"Retry-After": "1"},
            json={
                "error": {
                    "status": 429,
                    "message": "Too many requests",
                    "reason": "QUOTA_EXCEEDED",
                }
            },
        )
    )
    with pytest.raises(SpotifyAPIError) as exc_info:
        await client.get("/tracks/x")
    assert exc_info.value.status_code == 429
    assert "quota exceeded" in exc_info.value.message.lower()
    assert "developer account" in exc_info.value.message
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `uv run pytest tests/test_client.py -k quota -v`
Expected: FAIL (message is `Rate limited (retry after 1s)`).

- [ ] **Step 3: Implement**

In `client.py`, replace the final `raise` in the 429 branch:

```python
                raise SpotifyAPIError(
                    429,
                    f"Rate limited (retry after {retry_after}s)",
                    retry_after=retry_after,
                )
```

with

```python
                if self._extract_error_reason(response) == "QUOTA_EXCEEDED":
                    message = (
                        "Quota exceeded. Development-mode quota is shared by every Client ID "
                        f"on the developer account (retry after {retry_after}s)"
                    )
                else:
                    message = f"Rate limited (retry after {retry_after}s)"
                raise SpotifyAPIError(429, message, retry_after=retry_after)
```

Add below `_extract_error_message`:

```python
    @staticmethod
    def _extract_error_reason(response: httpx.Response) -> str | None:
        try:
            data = response.json()
        except ValueError:
            return None
        error = data.get("error") if isinstance(data, dict) else None
        return error.get("reason") if isinstance(error, dict) else None
```

- [ ] **Step 4: Run the tests and lint**

Run: `uv run pytest -q && uv run ruff check .`
Expected: all PASS (including the existing `test_429_exhausts_retries`), ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/spotify_mcp/client.py tests/test_client.py
git commit -m "feat: explain QUOTA_EXCEEDED 429 responses"
```

---

### Task 9: README, version bump, full verification, API review

**Files:**
- Modify: `README.md`
- Modify: `pyproject.toml` (`version`)

- [ ] **Step 1: Update README**
  - Features: change `- **Browse** - Get details on tracks, albums, artists, episodes, chapters — single or batch` to `- **Browse** - Get details on tracks, albums, artists, episodes, and chapters`.
  - Features: change `- **Follow** - Follow/unfollow artists, users, and playlists` to `- **Follow** - List followed artists; follow/unfollow artists, users, and playlists through the library tools by URI`. If **ARTIST_SUPPORTED = no**, drop "artists, " from the follow/unfollow part.
  - Tool tables: delete the rows for `get_albums`, `get_artists`, `get_tracks`, `get_shows`, `get_episodes`, `get_audiobooks`, `get_chapters`, `follow_artists_or_users`, `unfollow_artists_or_users`, `check_following`, `follow_playlist`, `unfollow_playlist`.
  - Library table: update the `save_to_library`, `remove_from_library`, and `check_saved_in_library` descriptions to mention follow/unfollow by artist/user/playlist URI, max 40 per request (auto-chunked).
  - Resources table: change the `spotify://me/profile` description to `Profile basics — display name, user ID, account ID`.
  - Add a short "Spotify API notes" section after "Configuration":

```markdown
## Spotify API notes

Development-mode Spotify apps have these restrictions (see the
[February 2026 migration guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide)):

- The app owner needs an active Spotify Premium subscription.
- API quota is shared by all Client IDs on the developer account. When it runs out, tools report `Quota exceeded`.
- Search returns at most 10 results per type.
- Full playlist contents are only returned for playlists you own or collaborate on.
```

- [ ] **Step 2: Bump the version**

`pyproject.toml`: `version = "0.2.0"` → `version = "0.3.0"`. Then run `uv lock` so `uv.lock` records the new version. The working tree already had an unrelated `uv.lock` modification before this plan; check `git diff uv.lock` and stage only the lines this bump changes. If the diff can't be separated, ask the user.

- [ ] **Step 3: Full verification**

Run: `uv run pytest -q && uv run ruff check . && uv run ruff format --check .`
Expected: all pass. Report the pass count. If any command fails, fix it or report it; don't proceed.

- [ ] **Step 4: API compliance review**

Invoke the `spotify-api-review` skill on the branch diff (`git diff main...HEAD`). Fix any finding it confirms, re-run Step 3, and commit the fixes as `fix: address spotify-api-review findings`.

- [ ] **Step 5: Final dead-reference sweep**

Run:

```bash
grep -rnE '"/(albums|artists|tracks|shows|episodes|audiobooks|chapters)"|/me/following"|/followers|get\("tracks"|get\("track"\)|popularity|publisher|"email"' src/ README.md
```

Expected: the only match is `"/me/following"` inside `get_followed_artists` (GET). Anything else is a leftover; fix it.

- [ ] **Step 6: Commit**

```bash
git add README.md pyproject.toml uv.lock
git commit -m "docs: update README for 2026 Web API changes; bump to 0.3.0"
```

---

### Task 10: Live smoke test before release (manual, no commit)

The stubbed tests can't catch API-side changes like the 40-URI limit. Run each tool once against a real dev-mode app before tagging 0.3.0. **This touches the user's real account.** Get their go-ahead first, and use a throwaway playlist for the write tools.

- [ ] **Step 1:** Re-authenticate so the reduced scope set applies. The user deletes `~/.spotify-mcp/credentials.json` themselves; it's outside the repo, so ask before touching it.
- [ ] **Step 2:** Through an MCP client (or `uv run mcp dev`), call each of: `search` (limit 10), `get_track`, `get_album`, `get_artist`, `get_show`, `get_episode`, `get_audiobook`, `get_chapter`, `get_playlist` (own and someone else's), `get_playlist_items`, `get_my_playlists`, `get_saved_shows`, `get_followed_artists`, `get_my_profile`, `whoami`, `save_to_library` → `check_saved_in_library` → `remove_from_library` (one track URI + one playlist URI, with artist included if ARTIST_SUPPORTED = yes), plus the `spotify://me/profile` resource.
- [ ] **Step 3:** Record any failing tool with its error message and report it to the user. Tagging and publishing 0.3.0 is the user's call and is out of scope for this plan.

**Task 10 results (2026-09-27, branch code at cec3c04, existing stored token, no re-auth):**
- OK: search (track/album/artist/show/episode), get_track, get_album, get_album_tracks, get_artist, get_episode, get_my_playlists, get_playlist (own), get_playlist_items, all get_saved_*, get_followed_artists, get_my_profile, whoami, get_recently_played, get_playback_state, get_currently_playing, get_devices, get_queue, get_my_top_items, all five resources.
- OK: save → check → remove → check round-trip for a track URI and an artist URI; library state restored.
- FAIL: `get_artist_albums` — 400 "Invalid limit": tool default 20 exceeds the spec maximum of 10 for `/artists/{id}/albums`.
- FAIL: `get_show`, `get_show_episodes` — crash on `null` entries in the episodes list.
- FAIL: `search` with `types=playlist` — crash on `null` entries in playlist results; so `get_playlist` (not owned) and the playlist-URI library round-trip were not exercised.
- Not exercised: audiobooks (no results for the account's market), playback-control and playlist-write tools (would change live playback / create persistent playlists).
