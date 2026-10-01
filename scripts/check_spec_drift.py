"""Check src/spotify_mcp against Spotify's OpenAPI spec.

Usage: python scripts/check_spec_drift.py [SPEC_PATH_OR_URL]

Exits 1 if the code calls an endpoint the spec deprecates or does not define,
or sends a `limit` above the spec maximum.
"""

from __future__ import annotations

import ast
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import yaml

SPEC_URL = "https://developer.spotify.com/reference/web-api/open-api-schema.yaml"
SRC_DIR = Path(__file__).resolve().parent.parent / "src" / "spotify_mcp"
HTTP_METHODS = {"get", "post", "put", "delete"}


@dataclass(frozen=True)
class Call:
    file: str
    line: int
    method: str
    path: str
    limit: int | None


def load_spec(source: str) -> dict:
    if source.startswith("http"):
        with urllib.request.urlopen(source) as response:
            return yaml.safe_load(response.read())
    return yaml.safe_load(Path(source).read_text())


def _path_template(node: ast.expr) -> str | None:
    """Render a string or f-string path, with each interpolation as `{}`."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(
            part.value if isinstance(part, ast.Constant) else "{}" for part in node.values
        )
    return None


def _function_limit(func: ast.AsyncFunctionDef) -> int | None:
    """The `limit` a tool sends by default: its parameter default, else a literal in a dict."""
    args = func.args
    names = [a.arg for a in args.posonlyargs + args.args]
    defaults = dict(zip(reversed(names), reversed(args.defaults), strict=False))
    default = defaults.get("limit")
    if isinstance(default, ast.Constant) and isinstance(default.value, int):
        return default.value
    for node in ast.walk(func):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values, strict=True):
            if (
                isinstance(key, ast.Constant)
                and key.value == "limit"
                and isinstance(value, ast.Constant)
                and isinstance(value.value, int)
            ):
                return value.value
    return None


def collect_calls(src_dir: Path) -> list[Call]:
    calls: set[Call] = set()
    for file in sorted(src_dir.rglob("*.py")):
        for func in ast.walk(ast.parse(file.read_text())):
            if not isinstance(func, ast.AsyncFunctionDef):
                continue
            limit = _function_limit(func)
            for node in ast.walk(func):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in HTTP_METHODS
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "client"
                    and node.args
                ):
                    path = _path_template(node.args[0])
                    if path and path.startswith("/"):
                        name = str(file.relative_to(src_dir))
                        calls.add(Call(name, node.lineno, node.func.attr, path, limit))
    return sorted(calls, key=lambda c: (c.file, c.line))


def _limit_maximum(spec: dict, operation: dict) -> int | None:
    for param in operation.get("parameters", []):
        if "$ref" in param:
            param = spec["components"]["parameters"][param["$ref"].rsplit("/", 1)[1]]
        if param.get("name") == "limit":
            return param.get("schema", {}).get("maximum")
    return None


def check(spec: dict, calls: list[Call]) -> list[str]:
    operations = [
        (re.compile(re.sub(r"\\\{[^}]+\\\}", "[^/]+", re.escape(path))), method, path, operation)
        for path, methods in spec["paths"].items()
        for method, operation in methods.items()
        if method in HTTP_METHODS
    ]
    problems = []
    for call in calls:
        where = f"{call.file}:{call.line} {call.method.upper()} {call.path}"
        concrete = call.path.replace("{}", "x")
        match = next(
            (
                (path, operation)
                for pattern, method, path, operation in operations
                if method == call.method and pattern.fullmatch(concrete)
            ),
            None,
        )
        if match is None:
            problems.append(f"{where}: not in the spec")
            continue
        spec_path, operation = match
        if operation.get("deprecated"):
            problems.append(f"{where}: {spec_path} is deprecated")
        maximum = _limit_maximum(spec, operation)
        if call.limit is not None and maximum is not None and call.limit > maximum:
            problems.append(f"{where}: limit {call.limit} exceeds the spec maximum of {maximum}")
    return problems


def main(argv: list[str]) -> int:
    spec = load_spec(argv[1] if len(argv) > 1 else SPEC_URL)
    calls = collect_calls(SRC_DIR)
    problems = check(spec, calls)
    for problem in problems:
        print(problem)
    if problems:
        return 1
    print(f"OK: {len(calls)} API calls checked against the spec")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
