from __future__ import annotations

import threading
import time
from datetime import UTC, datetime

from .config import Settings
from .devices import validate_session_devices
from .router import AudioRouter
from .store import SessionStore
from .stt import TranscriptionService
from .vad import SpeechSegmenter


class SessionManager:
    def __init__(self, settings: Settings, publish):
        self._settings = settings
        self._publish = publish
        self._store = SessionStore(settings.sessions_dir)
        self._lock = threading.RLock()
        self._session_id: str | None = None
        self._router: AudioRouter | None = None
        self._segmenters: dict[str, SpeechSegmenter] = {}
        self._stt: TranscriptionService | None = None
        self._started_at_ms = 0
        self._last_error: str | None = None

    def status(self) -> dict:
        with self._lock:
            return {
                "running": self._session_id is not None,
                "session_id": self._session_id,
                "model": self._settings.model_name,
                "last_error": self._last_error,
            }

    def start(self, mic_a: int, speaker_a: int, mic_b: int, speaker_b: int) -> dict:
        with self._lock:
            if self._session_id:
                raise ValueError("Sesi sudah berjalan.")
            validate_session_devices(mic_a, speaker_a, mic_b, speaker_b)
            self._last_error = None
            session_id = "ses_" + datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            self._session_id = session_id
            self._started_at_ms = int(time.time() * 1000)
            devices = {"mic_a": mic_a, "speaker_a": speaker_a, "mic_b": mic_b, "speaker_b": speaker_b}
            self._store.create(session_id, devices)
            self._stt = TranscriptionService(self._settings, self._on_final, self._on_error)
            self._segmenters = {
                speaker: SpeechSegmenter(
                    self._settings,
                    lambda audio, start, end, speaker=speaker: self._stt and self._stt.submit(speaker, audio, start, end),
                )
                for speaker in ("A", "B")
            }
            try:
                self._stt.start()
                for segmenter in self._segmenters.values():
                    segmenter.start()
                self._router = AudioRouter(
                    self._settings, mic_a, speaker_a, mic_b, speaker_b, self._on_audio
                )
                self._router.start()
            except Exception as exc:
                self._last_error = str(exc)
                self._cleanup()
                raise RuntimeError(f"Tidak dapat memulai sesi audio: {exc}") from exc
            self._publish({"type": "session.started", "session_id": session_id})
            return self.status()

    def stop(self) -> dict:
        with self._lock:
            if not self._session_id:
                return self.status()
            session_id = self._session_id
            self._cleanup()
            output = self._store.finish(session_id)
            self._publish({"type": "session.stopped", "session_id": session_id, "output": output.name})
            return {"running": False, "session_id": session_id, "output": output.name}

    def _on_audio(self, speaker: str, block, captured_at_ms: int) -> None:
        segmenter = self._segmenters.get(speaker)
        if segmenter:
            segmenter.push(block, captured_at_ms)

    def _on_final(self, speaker: str, text: str, started_at_ms: int, ended_at_ms: int) -> None:
        session_id = self._session_id
        if not session_id:
            return
        event = {
            "type": "transcript.final",
            "session_id": session_id,
            "speaker": speaker,
            "text": text,
            "started_at_ms": started_at_ms - self._started_at_ms,
            "ended_at_ms": ended_at_ms - self._started_at_ms,
            "is_final": True,
        }
        self._store.add(session_id, event)
        self._publish(event)

    def _on_error(self, speaker: str, error: str) -> None:
        self._last_error = error
        self._publish({"type": "transcript.error", "speaker": speaker, "error": error})

    def _cleanup(self) -> None:
        if self._router:
            self._router.stop()
        for segmenter in self._segmenters.values():
            segmenter.stop()
        if self._stt:
            self._stt.stop()
        self._router = None
        self._segmenters = {}
        self._stt = None
        self._session_id = None
