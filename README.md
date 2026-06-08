# Spotify MCP Server

[![PyPI](https://img.shields.io/pypi/v/mcp-server-spotify.svg)](https://pypi.org/project/mcp-server-spotify/)

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that provides tools for interacting with the Spotify Web API. Enables AI assistants like Claude to search music, control playback, manage playlists, and more.

## Features

- **Search** - Find tracks, albums, artists, playlists, shows, episodes, and audiobooks
- **Playback Control** - Play, pause, skip, seek, volume, shuffle, repeat, queue management
- **Playlists** - Create, update, add/remove/reorder tracks (auto-chunks large batches)
- **Library** - View and manage saved tracks, albums, shows, episodes, and audiobooks
- **Browse** - Get details on tracks, albums, artists, episodes, chapters — single or batch
- **Podcasts & Audiobooks** - Browse shows, episodes, audiobooks, and chapters
- **Follow** - Follow/unfollow artists, users, and playlists
- **User Profile** - View profile, top artists/tracks, diagnostic `whoami`
- **Resources** - Subscribable snapshots of profile, playback, queue, top items
- **Prompts** - Pre-baked workflows for playlist building, listening summaries, library cleanup
- **Transports** - `stdio` (default), `sse`, and `streamable-http`
- Covers all non-deprecated Spotify Web API endpoints

## Example interactions

Once configured, ask your AI assistant things like:

- "What am I listening to right now?"
- "Play some Radiohead on my living room speaker."
- "Skip this track and turn the volume down to 30."
- "Build me a playlist of 25 chill tracks based on what I've been listening to this week."
- "Add the last three songs I played to my 'Focus' playlist."
- "Show me my top artists from the last six months."
- "Search for live albums by Nils Frahm and save the best one to my library."
- "Unfollow every playlist I haven't opened that wasn't made by me."
- "Queue up the next episode of the show I was listening to yesterday."

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — install with `curl -LsSf https://astral.sh/uv/install.sh | sh`
- A [Spotify Developer](https://developer.spotify.com/dashboard) account
- A Spotify app with Client ID and Client Secret

## Getting Your Spotify Credentials

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Click **Create App**
3. Fill in the app details:
   - **App name**: Choose any name (e.g., "My MCP Server")
   - **App description**: Optional
   - **Redirect URI**: `http://127.0.0.1:8888/callback`
   - **Which API/SDKs are you planning to use?**: Select **Web API**
4. Click **Save**
5. On your app's page, find your **Client ID**
6. Click **Show client secret** to reveal your **Client Secret**

> **Important**: The redirect URI must exactly match `http://127.0.0.1:8888/callback` (or whatever you set in `SPOTIFY_REDIRECT_URI`). Do not use `localhost` — use `127.0.0.1`.

## Installation

Pick your client below. All examples use `uvx` to fetch the server on demand — no clone, no manual install.

### Claude Code

```bash
claude mcp add spotify \
  -e SPOTIFY_CLIENT_ID=your_client_id \
  -e SPOTIFY_CLIENT_SECRET=your_client_secret \
  -- uvx mcp-server-spotify
```

### Other MCP clients

Most MCP clients configure servers via a JSON file. Add this entry to your client's MCP config:

```json
{
  "mcpServers": {
    "spotify": {
      "command": "uvx",
      "args": ["mcp-server-spotify"],
      "env": {
        "SPOTIFY_CLIENT_ID": "your_client_id",
        "SPOTIFY_CLIENT_SECRET": "your_client_secret"
      }
    }
  }
}
```

### Running from a local checkout

For development, or if you want to run a modified copy:

```bash
git clone https://github.com/llyfn/spotify-mcp.git
cd spotify-mcp && uv sync
```

Then point your client at the local checkout instead of `uvx`:

```jsonc
"command": "uv",
"args": ["--directory", "/absolute/path/to/spotify-mcp", "run", "mcp-server-spotify"]
```

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SPOTIFY_CLIENT_ID` | Yes | — | Your Spotify app's Client ID |
| `SPOTIFY_CLIENT_SECRET` | Yes | — | Your Spotify app's Client Secret |
| `SPOTIFY_REDIRECT_URI` | No | `http://127.0.0.1:8888/callback` | OAuth redirect URI |
| `SPOTIFY_MCP_TRANSPORT` | No | `stdio` | MCP transport: `stdio`, `sse`, or `streamable-http` |

## Authentication

The server uses Spotify's **Authorization Code** flow:

1. On first use, the server opens your browser to Spotify's login page
2. Spotify will ask you to approve access — the server requests all scopes needed for the full tool set (playback, library, playlists, and user data)
3. After you authorize, Spotify redirects to the local callback server
4. The server exchanges the authorization code for access/refresh tokens
5. Tokens are stored securely in `~/.spotify-mcp/credentials.json`
6. Tokens are automatically refreshed when they expire

If running in a headless environment (SSH, Docker), the auth URL will be printed to stderr — copy and paste it into a browser manually.

### Re-authenticating

To re-authenticate (e.g., after revoking access), delete the stored credentials:

```bash
rm ~/.spotify-mcp/credentials.json
```

## Available Tools

### Search
| Tool | Description |
|------|-------------|
| `search` | Search for tracks, albums, artists, playlists, shows, episodes, or audiobooks |

### Albums
| Tool | Description |
|------|-------------|
| `get_album` | Get album details by ID |
| `get_albums` | Batch lookup — up to 20 album IDs in one call |
| `get_album_tracks` | Get tracks in an album |

### Artists
| Tool | Description |
|------|-------------|
| `get_artist` | Get artist details by ID |
| `get_artists` | Batch lookup — up to 50 artist IDs in one call |
| `get_artist_albums` | Get albums by an artist |

### Tracks
| Tool | Description |
|------|-------------|
| `get_track` | Get track details by ID |
| `get_tracks` | Batch lookup — up to 50 track IDs in one call |

### Playlists
| Tool | Description |
|------|-------------|
| `get_playlist` | Get playlist details |
| `update_playlist` | Update playlist name, description, or visibility |
| `get_playlist_items` | Get items in a playlist |
| `add_playlist_items` | Add tracks/episodes to a playlist |
| `remove_playlist_items` | Remove items from a playlist |
| `reorder_playlist_items` | Reorder items in a playlist |
| `get_my_playlists` | Get the current user's playlists |
| `create_playlist` | Create a new playlist |

### Library
| Tool | Description |
|------|-------------|
| `get_saved_tracks` | Get saved tracks |
| `get_saved_albums` | Get saved albums |
| `get_saved_shows` | Get saved shows |
| `get_saved_episodes` | Get saved episodes |
| `get_saved_audiobooks` | Get saved audiobooks |
| `save_to_library` | Save items to library |
| `remove_from_library` | Remove items from library |
| `check_saved_in_library` | Check if items are in library |

### Player
| Tool | Description |
|------|-------------|
| `get_playback_state` | Get current playback state |
| `get_currently_playing` | Get the currently playing track |
| `play` | Start or resume playback |
| `pause` | Pause playback |
| `next_track` | Skip to next track |
| `previous_track` | Skip to previous track |
| `seek` | Seek to position in track |
| `set_repeat` | Set repeat mode (track/context/off) |
| `set_volume` | Set playback volume |
| `toggle_shuffle` | Toggle shuffle mode |
| `transfer_playback` | Transfer playback to another device |
| `get_devices` | Get available devices |
| `add_to_queue` | Add item to playback queue |
| `get_queue` | Get the playback queue |
| `get_recently_played` | Get recently played tracks |

### Shows & Podcasts
| Tool | Description |
|------|-------------|
| `get_show` | Get show details |
| `get_shows` | Batch lookup — up to 50 show IDs in one call |
| `get_show_episodes` | Get episodes of a show |
| `get_episode` | Get a single episode by ID |
| `get_episodes` | Batch lookup — up to 50 episode IDs in one call |

### Audiobooks
| Tool | Description |
|------|-------------|
| `get_audiobook` | Get audiobook details |
| `get_audiobooks` | Batch lookup — up to 50 audiobook IDs in one call |
| `get_audiobook_chapters` | Get chapters of an audiobook |
| `get_chapter` | Get chapter details |
| `get_chapters` | Batch lookup — up to 50 chapter IDs in one call |

### Follow
| Tool | Description |
|------|-------------|
| `get_followed_artists` | List artists the user follows (cursor-paginated) |
| `follow_artists_or_users` | Follow one or more artists or users by ID |
| `unfollow_artists_or_users` | Unfollow one or more artists or users by ID |
| `check_following` | Check whether the user follows given artist/user IDs |
| `follow_playlist` | Follow a playlist (optionally publicly) |
| `unfollow_playlist` | Unfollow a playlist |

### Users
| Tool | Description |
|------|-------------|
| `get_my_profile` | Get current user's profile |
| `get_my_top_items` | Get top artists or tracks |
| `whoami` | Diagnostic — auth status, active device, configured scopes |

## Resources

Snapshots of user state exposed under the `spotify://` URI scheme. MCP clients can
include them as context or subscribe for updates without calling a tool.

| URI | Description |
|-----|-------------|
| `spotify://me/profile` | Profile basics — name, country, plan, follower count |
| `spotify://me/playback` | Current playback state (episode-aware) |
| `spotify://me/queue` | Currently playing + next-up queue |
| `spotify://me/top/tracks` | Top tracks (last ~6 months) |
| `spotify://me/top/artists` | Top artists (last ~6 months) |

## Prompts

Canned workflows MCP clients can offer in their prompt picker. Each one walks the
assistant through a multi-step task using the tools above.

| Prompt | Description |
|--------|-------------|
| `build_playlist_from_recent` | Build a new playlist seeded by recent listening (`n_tracks`) |
| `weekly_listening_summary` | Summarize the past week's listening grouped by artist/album |
| `playlist_from_artists` | Build a playlist from a comma-separated list of artists (`artists`, `tracks_per_artist`) |
| `library_cleanup` | Scan saved tracks and propose cleanup candidates (`scan_size`) |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT - see [LICENSE](LICENSE) for details.
