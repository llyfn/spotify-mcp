"""Check src/spotify_mcp against Spotify's OpenAPI spec.

Usage: python scripts/check_spec_drift.py [SPEC_PATH_OR_URL]

Exits 1 if the code calls an endpoint the spec deprecates or does not define,
or has a default `limit` above the spec maximum.
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
    path: str | None
    limit: int | None


def load_spec(source: str) -> dict:
    if source.startswith("http"):
        with urllib.request.urlopen(source, timeout=30) as response:
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


def _parameter_defaults(func: ast.AsyncFunctionDef) -> dict[str, ast.expr]:
    args = func.args
    names = [a.arg for a in args.posonlyargs + args.args]
    defaults = dict(zip(reversed(names), reversed(args.defaults), strict=False))
    defaults.update(
        {a.arg: d for a, d in zip(args.kwonlyargs, args.kw_defaults, strict=True) if d is not None}
    )
    return defaults


def _dict_assigned_to(func: ast.AsyncFunctionDef, name: str) -> ast.Dict | None:
    for node in ast.walk(func):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if isinstance(node.value, ast.Dict) and any(
            isinstance(target, ast.Name) and target.id == name for target in targets
        ):
            return node.value
    return None


def _call_limit(func: ast.AsyncFunctionDef, call: ast.Call) -> int | None:
    """The `limit` this call sends by default, read from its `params` argument."""
    params = next((k.value for k in call.keywords if k.arg == "params"), None)
    if isinstance(params, ast.Name):
        params = _dict_assigned_to(func, params.id)
    if not isinstance(params, ast.Dict):
        return None
    for key, value in zip(params.keys, params.values, strict=True):
        if isinstance(key, ast.Constant) and key.value == "limit":
            if isinstance(value, ast.Name):
                value = _parameter_defaults(func).get(value.id)
            if isinstance(value, ast.Constant) and isinstance(value.value, int):
                return value.value
    return None


def collect_calls(src_dir: Path) -> list[Call]:
    calls: set[Call] = set()
    for file in sorted(src_dir.rglob("*.py")):
        for func in ast.walk(ast.parse(file.read_text())):
            if not isinstance(func, ast.AsyncFunctionDef):
                continue
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
                    if path is None or path.startswith("/"):
                        name = str(file.relative_to(src_dir))
                        limit = _call_limit(func, node)
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
        if call.path is None:
            continue
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
        if call.limit is not None and call.method == "get":
            if maximum is None:
                problems.append(f"{where}: sends a limit but the spec defines no maximum for it")
            elif call.limit > maximum:
                problems.append(
                    f"{where}: limit {call.limit} exceeds the spec maximum of {maximum}"
                )
    return problems


def main(argv: list[str]) -> int:
    spec = load_spec(argv[1] if len(argv) > 1 else SPEC_URL)
    calls = collect_calls(SRC_DIR)
    problems = check(spec, calls)
    skipped = [f"{call.file}:{call.line}" for call in calls if call.path is None]
    checked = len(calls) - len(skipped)
    ok = not problems and checked > 0
    for problem in problems:
        print(problem)
    if ok:
        print(f"OK: {checked} API calls checked against the spec")
    elif not problems:
        print("No API calls found to check")
    if skipped:
        print(f"Not checked, path is not a string literal: {', '.join(skipped)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
