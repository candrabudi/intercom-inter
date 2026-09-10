from __future__ import annotations

from collections.abc import Callable
from threading import RLock
from typing import Any


class EventBus:
    """Small in-process event bus shared by audio, STT, and delivery layers."""

    def __init__(self) -> None:
        self._handlers: list[Callable[[dict[str, Any]], None]] = []
        self._lock = RLock()

    def subscribe(self, handler: Callable[[dict[str, Any]], None]) -> None:
        with self._lock:
            self._handlers.append(handler)

    def publish(self, event: dict[str, Any]) -> None:
        with self._lock:
            handlers = tuple(self._handlers)
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                print(f"Event handler error: {exc}")
