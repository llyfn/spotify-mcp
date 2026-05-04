# Spotify MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that provides tools for interacting with the Spotify Web API. Enables AI assistants like Claude to search music, control playback, manage playlists, and more.

## Features

- **Search** - Find tracks, albums, artists, playlists, shows, episodes, and audiobooks
- **Playback Control** - Play, pause, skip, seek, volume, shuffle, repeat, queue management
- **Playlists** - Create, update, add/remove/reorder tracks
- **Library** - View and manage saved tracks, albums, shows, episodes, and audiobooks
- **Browse** - Get album details, artist info, track metadata
- **Podcasts & Audiobooks** - Browse shows, episodes, audiobooks, and chapters
- **User Profile** - View profile, top artists/tracks, followed artists
- **44 tools** covering non-deprecated Spotify Web API endpoints

## Prerequisites

- Python 3.12+
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

### Using uvx (Recommended)

No installation needed. Configure your MCP client to run the server directly:

```json
{
  "mcpServers": {
    "spotify": {
      "command": "uvx",
      "args": ["spotifymcp"],
      "env": {
        "SPOTIFY_CLIENT_ID": "your_client_id",
        "SPOTIFY_CLIENT_SECRET": "your_client_secret"
      }
    }
  }
}
```

### Local Installation

Clone the repository and install with `uv`:

```bash
git clone https://github.com/llyfn/spotify-mcp.git
cd spotify-mcp
uv sync
```

Then configure your MCP client:

```json
{
  "mcpServers": {
    "spotify": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/spotify-mcp", "run", "spotifymcp"],
      "env": {
        "SPOTIFY_CLIENT_ID": "your_client_id",
        "SPOTIFY_CLIENT_SECRET": "your_client_secret"
      }
    }
  }
}
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SPOTIFY_CLIENT_ID` | Yes | — | Your Spotify app's Client ID |
| `SPOTIFY_CLIENT_SECRET` | Yes | — | Your Spotify app's Client Secret |
| `SPOTIFY_REDIRECT_URI` | No | `http://127.0.0.1:8888/callback` | OAuth redirect URI |

### MCP Client Configuration

<details>
<summary><strong>Claude Desktop</strong></summary>

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%AppData%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "spotify": {
      "command": "uvx",
      "args": ["spotifymcp"],
      "env": {
        "SPOTIFY_CLIENT_ID": "your_client_id",
        "SPOTIFY_CLIENT_SECRET": "your_client_secret"
      }
    }
  }
}
```
</details>

<details>
<summary><strong>Claude Code</strong></summary>

```bash
claude mcp add spotify -- uvx spotifymcp
```

Set the environment variables in your shell profile or `.env` file:

```bash
export SPOTIFY_CLIENT_ID="your_client_id"
export SPOTIFY_CLIENT_SECRET="your_client_secret"
```
</details>

<details>
<summary><strong>Cursor</strong></summary>

Add to `.cursor/mcp.json` in your project:

```json
{
  "mcpServers": {
    "spotify": {
      "command": "uvx",
      "args": ["spotifymcp"],
      "env": {
        "SPOTIFY_CLIENT_ID": "your_client_id",
        "SPOTIFY_CLIENT_SECRET": "your_client_secret"
      }
    }
  }
}
```
</details>

## Authentication

The server uses Spotify's **Authorization Code** flow:

1. On first use, the server opens your browser to Spotify's login page
2. After you authorize, Spotify redirects to the local callback server
3. The server exchanges the authorization code for access/refresh tokens
4. Tokens are stored securely in `~/.spotify-mcp/credentials.json`
5. Tokens are automatically refreshed when they expire

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
| `get_album_tracks` | Get tracks in an album |

### Artists
| Tool | Description |
|------|-------------|
| `get_artist` | Get artist details by ID |
| `get_artist_albums` | Get albums by an artist |

### Tracks
| Tool | Description |
|------|-------------|
| `get_track` | Get track details by ID |

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
| `get_show_episodes` | Get episodes of a show |

### Audiobooks
| Tool | Description |
|------|-------------|
| `get_audiobook` | Get audiobook details |
| `get_audiobook_chapters` | Get chapters of an audiobook |
| `get_chapter` | Get chapter details |

### Users
| Tool | Description |
|------|-------------|
| `get_my_profile` | Get current user's profile |
| `get_my_top_items` | Get top artists or tracks |

> Following artists/users uses the same `save_to_library` / `remove_from_library` / `check_saved_in_library` tools — pass an artist or user URI.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT - see [LICENSE](LICENSE) for details.
