from __future__ import annotations

from dataclasses import dataclass

from .application.event_bus import EventBus
from .config import Settings, settings
from .mic_test import LiveMicTestManager
from .session import SessionManager
from .websocket import WebSocketHub


@dataclass
class AppContainer:
    """Composition root: the only place where runtime services are wired."""

    settings: Settings
    events: EventBus
    hub: WebSocketHub
    session: SessionManager
    mic_test: LiveMicTestManager


def build_container(app_settings: Settings = settings) -> AppContainer:
    events = EventBus()
    hub = WebSocketHub()
    events.subscribe(hub.publish_from_thread)
    session = SessionManager(app_settings, events.publish)
    mic_test = LiveMicTestManager(app_settings, events.publish)
    return AppContainer(app_settings, events, hub, session, mic_test)
