from __future__ import annotations

import asyncio

import pytest

from tests.live._helpers import Live, first_id, require


async def test_playback_controls(live: Live) -> None:
    require("SPOTIFY_LIVE_PLAYBACK")
    state = await live.client.get("/me/player", params={"additional_types": "episode"})
    if not state or not state.get("device"):
        pytest.skip("no active Spotify device; start playback on a device first")
    device = state["device"]
    volume = device.get("volume_percent")
    can_set_volume = volume is not None and device.get("supports_volume", True)
    found = await live.call("search", query="Nils Frahm", types="track", limit=1)
    track_id = first_id(found)
    assert track_id
    track_uri = f"spotify:track:{track_id}"

    async def step(tool: str, **args: object) -> None:
        await live.call(tool, **args)
        await asyncio.sleep(1)

    try:
        if state["is_playing"]:
            await step("pause")
            await step("play")
        else:
            await step("play")
            await step("pause")
            await step("play")
        await step("seek", position_ms=0)
        await step("add_to_queue", uri=track_uri)
        await step("next_track")
        await step("previous_track")
        await step("toggle_shuffle", state=not state["shuffle_state"])
        await step("set_repeat", state="track")
        if can_set_volume:
            await step("set_volume", volume_percent=max(volume - 5, 0))
        await step("transfer_playback", device_id=device["id"], play=True)
    finally:
        restores: list[tuple[str, dict[str, object]]] = [
            ("toggle_shuffle", {"state": state["shuffle_state"]}),
            ("set_repeat", {"state": state["repeat_state"]}),
        ]
        if can_set_volume:
            restores.append(("set_volume", {"volume_percent": volume}))
        errors = []
        for tool, args in restores:
            try:
                await step(tool, **args)
            except Exception as error:
                errors.append(f"{tool}: {error}")
        try:
            current = await live.client.get("/me/player")
            if current and current.get("is_playing") != state["is_playing"]:
                await step("play" if state["is_playing"] else "pause")
        except Exception as error:
            errors.append(f"play/pause: {error}")
        assert not errors, f"could not restore playback state: {errors}"
