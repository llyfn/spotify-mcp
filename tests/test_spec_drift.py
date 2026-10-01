from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).parent.parent / "scripts" / "check_spec_drift.py"

SPEC = {
    "paths": {
        "/artists/{id}/albums": {
            "get": {
                "parameters": [
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "maximum": 10}}
                ]
            }
        },
        "/me/tracks": {"get": {"parameters": [{"$ref": "#/components/parameters/QueryLimit"}]}},
        "/tracks": {"get": {"deprecated": True}},
        "/me/library": {"put": {}},
    },
    "components": {
        "parameters": {"QueryLimit": {"name": "limit", "in": "query", "schema": {"maximum": 50}}}
    },
}


@pytest.fixture
def drift() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_spec_drift", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves annotations through sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _problems(drift: ModuleType, tmp_path: Path, source: str) -> list[str]:
    (tmp_path / "tool.py").write_text(source)
    return drift.check(SPEC, drift.collect_calls(tmp_path))


def test_clean_source_reports_nothing(drift: ModuleType, tmp_path: Path) -> None:
    source = (
        "async def albums(client, artist_id, limit: int = 10):\n"
        '    await client.get(f"/artists/{artist_id}/albums", params={"limit": limit})\n'
        "async def save(client, uris):\n"
        '    await client.put("/me/library", params={"uris": uris})\n'
    )
    assert _problems(drift, tmp_path, source) == []


def test_reports_a_deprecated_endpoint(drift: ModuleType, tmp_path: Path) -> None:
    source = (
        'async def tracks(client, ids):\n    await client.get("/tracks", params={"ids": ids})\n'
    )
    assert _problems(drift, tmp_path, source) == ["tool.py:2 GET /tracks: /tracks is deprecated"]


def test_reports_an_endpoint_missing_from_the_spec(drift: ModuleType, tmp_path: Path) -> None:
    source = 'async def gone(client):\n    await client.get("/me/nonexistent")\n'
    assert _problems(drift, tmp_path, source) == ["tool.py:2 GET /me/nonexistent: not in the spec"]


def test_reports_a_default_limit_above_the_spec_maximum(drift: ModuleType, tmp_path: Path) -> None:
    source = (
        "async def albums(client, artist_id, limit: int = 20):\n"
        '    await client.get(f"/artists/{artist_id}/albums", params={"limit": limit})\n'
    )
    assert _problems(drift, tmp_path, source) == [
        "tool.py:2 GET /artists/{}/albums: limit 20 exceeds the spec maximum of 10"
    ]


def test_reports_a_literal_limit_resolved_through_a_ref(drift: ModuleType, tmp_path: Path) -> None:
    source = 'async def saved(client):\n    await client.get("/me/tracks", params={"limit": 60})\n'
    assert _problems(drift, tmp_path, source) == [
        "tool.py:2 GET /me/tracks: limit 60 exceeds the spec maximum of 50"
    ]


def test_ignores_calls_with_non_literal_paths(drift: ModuleType, tmp_path: Path) -> None:
    source = "async def passthrough(client, path):\n    await client.get(path)\n"
    assert _problems(drift, tmp_path, source) == []
