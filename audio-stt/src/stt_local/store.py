from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path


class SessionStore:
    def __init__(self, sessions_dir: Path):
        self._sessions_dir = sessions_dir
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._events: dict[str, list[dict]] = {}
        self._devices: dict[str, dict[str, int]] = {}

    def create(self, session_id: str, devices: dict[str, int]) -> None:
        with self._lock:
            self._events[session_id] = []
            self._devices[session_id] = devices
            self._write(session_id, devices)

    def add(self, session_id: str, event: dict) -> None:
        with self._lock:
            self._events.setdefault(session_id, []).append(event)
            self._write(session_id, {})

    def finish(self, session_id: str) -> Path:
        with self._lock:
            self._write(session_id, {})
            txt = self._sessions_dir / f"{session_id}.txt"
            events = sorted(self._events.get(session_id, []), key=lambda item: item["started_at_ms"])
            lines = [
                f"[{event['speaker']}] {event['text']}"
                for event in events
                if event.get("type") == "transcript.final"
            ]
            txt.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
            return txt

    def _write(self, session_id: str, devices: dict[str, int]) -> None:
        output = {
            "session_id": session_id,
            "updated_at": datetime.now(UTC).isoformat(),
            "devices": devices or self._devices.get(session_id, {}),
            "events": self._events.get(session_id, []),
        }
        (self._sessions_dir / f"{session_id}.json").write_text(
            json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
        )
