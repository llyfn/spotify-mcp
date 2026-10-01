from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from spotify_mcp.tools import register_all_tools

LIVE_DIR = Path(__file__).parent / "live"


async def test_every_tool_has_a_live_test() -> None:
    mcp = FastMCP("test")
    register_all_tools(mcp, None)  # type: ignore[arg-type]
    live_source = "".join(path.read_text() for path in sorted(LIVE_DIR.glob("test_*.py")))
    missing = sorted(
        tool.name for tool in await mcp.list_tools() if f'"{tool.name}"' not in live_source
    )
    assert not missing, f"tools with no live test: {missing}"
