from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest
import yaml

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
        "/me/player/devices": {"get": {}},
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


def test_non_literal_paths_are_collected_but_not_checked(drift: ModuleType, tmp_path: Path) -> None:
    source = "async def passthrough(client, path):\n    await client.get(path)\n"
    assert _problems(drift, tmp_path, source) == []
    assert [call.path for call in drift.collect_calls(tmp_path)] == [None]


def test_checks_a_dict_literal_limit_larger_than_the_parameter_default(
    drift: ModuleType, tmp_path: Path
) -> None:
    source = (
        "async def saved(client, limit: int = 10):\n"
        '    await client.get("/me/tracks", params={"limit": 60})\n'
    )
    assert _problems(drift, tmp_path, source) == [
        "tool.py:2 GET /me/tracks: limit 60 exceeds the spec maximum of 50"
    ]


def test_checks_a_keyword_only_limit_default(drift: ModuleType, tmp_path: Path) -> None:
    source = (
        "async def albums(client, artist_id, *, limit: int = 20):\n"
        '    await client.get(f"/artists/{artist_id}/albums", params={"limit": limit})\n'
    )
    assert _problems(drift, tmp_path, source) == [
        "tool.py:2 GET /artists/{}/albums: limit 20 exceeds the spec maximum of 10"
    ]


def test_reports_a_limit_sent_where_the_spec_defines_no_maximum(
    drift: ModuleType, tmp_path: Path
) -> None:
    source = (
        "async def devices(client, limit: int = 5):\n"
        '    await client.get("/me/player/devices", params={"limit": limit})\n'
    )
    assert _problems(drift, tmp_path, source) == [
        "tool.py:2 GET /me/player/devices: sends a limit but the spec defines no maximum for it"
    ]


def test_main_fails_when_it_checks_no_calls(
    drift: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text(yaml.safe_dump(SPEC))
    src = tmp_path / "src"
    src.mkdir()
    monkeypatch.setattr(drift, "SRC_DIR", src)
    assert drift.main(["check_spec_drift.py", str(spec_file)]) == 1


def test_main_passes_on_a_clean_source_tree(
    drift: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text(yaml.safe_dump(SPEC))
    src = tmp_path / "src"
    src.mkdir()
    (src / "tool.py").write_text(
        'async def devices(client):\n    await client.get("/me/player/devices")\n'
    )
    monkeypatch.setattr(drift, "SRC_DIR", src)
    assert drift.main(["check_spec_drift.py", str(spec_file)]) == 0


def test_a_limit_is_attributed_only_to_the_call_that_sends_it(
    drift: ModuleType, tmp_path: Path
) -> None:
    source = (
        "async def both(client, limit: int = 5):\n"
        '    await client.get("/me/player/devices")\n'
        '    await client.get("/me/tracks", params={"limit": limit})\n'
    )
    assert _problems(drift, tmp_path, source) == []


def test_checks_a_limit_in_a_params_dict_passed_by_name(drift: ModuleType, tmp_path: Path) -> None:
    source = (
        "async def saved(client, limit: int = 60):\n"
        '    params: dict = {"limit": limit, "offset": 0}\n'
        '    await client.get("/me/tracks", params=params)\n'
    )
    assert _problems(drift, tmp_path, source) == [
        "tool.py:3 GET /me/tracks: limit 60 exceeds the spec maximum of 50"
    ]


def test_main_lists_unchecked_calls_even_when_it_finds_problems(
    drift: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text(yaml.safe_dump(SPEC))
    src = tmp_path / "src"
    src.mkdir()
    (src / "tool.py").write_text(
        "async def tracks(client, ids, path):\n"
        '    await client.get("/tracks", params={"ids": ids})\n'
        "    await client.get(path)\n"
    )
    monkeypatch.setattr(drift, "SRC_DIR", src)
    assert drift.main(["check_spec_drift.py", str(spec_file)]) == 1
    output = capsys.readouterr().out
    assert "/tracks is deprecated" in output
    assert "Not checked, path is not a string literal: tool.py:3" in output
