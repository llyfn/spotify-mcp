from __future__ import annotations

from typing import Any


class StubClient:
    """Records every call. Optional canned responses keyed by (method, path)."""

    def __init__(self, responses: dict[tuple[str, str], Any] | None = None) -> None:
        self._responses = responses or {}
        self.calls: list[tuple[str, str, dict | None, Any]] = []

    async def _do(self, method: str, path: str, **kwargs: Any) -> Any:
        params = kwargs.get("params")
        json_body = kwargs.get("json")
        self.calls.append((method, path, params, json_body))
        resp = self._responses.get((method, path), {})
        if callable(resp):
            return resp(len([c for c in self.calls if c[0] == method and c[1] == path]) - 1)
        return resp

    async def get(self, path: str, params: dict | None = None) -> Any:
        return await self._do("GET", path, params=params)

    async def post(self, path: str, params: dict | None = None, json: Any = None) -> Any:
        return await self._do("POST", path, params=params, json=json)

    async def put(self, path: str, params: dict | None = None, json: Any = None) -> Any:
        return await self._do("PUT", path, params=params, json=json)

    async def delete(self, path: str, params: dict | None = None, json: Any = None) -> Any:
        return await self._do("DELETE", path, params=params, json=json)


def flatten(result: Any) -> str:
    """Text of a `call_tool` result, which is a content list or a (list, dict) tuple."""
    if isinstance(result, tuple):
        result = result[0]
    parts: list[str] = []
    for item in result:
        text = getattr(item, "text", None)
        if text is not None:
            parts.append(text)
    return "\n".join(parts) if parts else str(result)
