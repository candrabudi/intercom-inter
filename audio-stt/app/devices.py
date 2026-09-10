from __future__ import annotations

from typing import Any

import sounddevice as sd


_ALIAS_PREFIXES = ("microsoft sound mapper", "primary sound capture driver", "primary sound driver")
_SYSTEM_INPUT_MARKERS = ("stereo mix", "loopback", "what u hear")
_SPEAKER_MARKERS = ("speaker", "speakers", "headphone", "headset", "output")


def _is_alias(name: str) -> bool:
    return name.lower().startswith(_ALIAS_PREFIXES)


def _kind(name: str, max_input_channels: int, max_output_channels: int) -> str:
    normalized = name.lower()
    if any(marker in normalized for marker in _SYSTEM_INPUT_MARKERS):
        return "system-input"
    if max_output_channels > 0 or any(marker in normalized for marker in _SPEAKER_MARKERS):
        return "speaker"
    if max_input_channels > 0:
        return "microphone"
    return "other"


def list_devices() -> list[dict[str, Any]]:
    """Return classified audio endpoints, preferring native WASAPI hardware devices."""
    devices: list[dict[str, Any]] = []
    for index, device in enumerate(sd.query_devices()):
        name = device["name"]
        hostapi = sd.query_hostapis(device["hostapi"])["name"]
        kind = _kind(name, device["max_input_channels"], device["max_output_channels"])
        devices.append({
            "id": index, "name": name, "hostapi": hostapi, "kind": kind,
            "is_alias": _is_alias(name), "max_input_channels": device["max_input_channels"],
            "max_output_channels": device["max_output_channels"], "default_samplerate": device["default_samplerate"],
        })

    for kind in ("microphone", "speaker"):
        candidates = [item for item in devices if item["kind"] == kind and not item["is_alias"]]
        has_wasapi = any(item["hostapi"] == "Windows WASAPI" for item in candidates)
        for item in candidates:
            item["selectable"] = not has_wasapi or item["hostapi"] == "Windows WASAPI"
    for item in devices:
        item.setdefault("selectable", False)
    return devices


def _find_device(device_id: int, expected_kind: str) -> dict[str, Any]:
    device = next((item for item in list_devices() if item["id"] == device_id), None)
    if device is None:
        raise ValueError(f"Perangkat {device_id} tidak ditemukan.")
    if device["kind"] != expected_kind or not device["selectable"]:
        raise ValueError(f"Perangkat {device_id} bukan {expected_kind} fisik yang dapat dipilih.")
    return device


def validate_input(device_id: int) -> None:
    _find_device(device_id, "microphone")


def input_candidates(device_id: int) -> list[int]:
    """Try the selected endpoint first, then compatible views of the same microphone."""
    selected = _find_device(device_id, "microphone")
    candidates = [selected["id"]]
    # Some Intel Windows drivers expose a failing WASAPI endpoint but work through MME/DirectSound.
    for item in list_devices():
        if item["id"] == selected["id"] or item["kind"] != "microphone" or item["is_alias"]:
            continue
        if item["hostapi"] in ("MME", "Windows DirectSound", "Windows WDM-KS"):
            candidates.append(item["id"])
    return candidates


def validate_output(device_id: int) -> None:
    _find_device(device_id, "speaker")


def validate_session_devices(mic_a: int, speaker_a: int, mic_b: int, speaker_b: int) -> None:
    validate_input(mic_a)
    validate_input(mic_b)
    validate_output(speaker_a)
    validate_output(speaker_b)
    if mic_a == mic_b:
        raise ValueError("Mic A dan Mic B harus perangkat yang berbeda.")
    if speaker_a == speaker_b:
        raise ValueError("Speaker A dan Speaker B harus perangkat yang berbeda.")
