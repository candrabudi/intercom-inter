from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import replace

import numpy as np
import sounddevice as sd

from .devices import input_candidates, validate_input
from .config import Settings
from .infrastructure.stt.whisper import TranscriptionService
from .vad import SpeechSegmenter


class MicrophoneTester:
    """Captures one microphone and publishes a throttled visual level meter."""

    def __init__(self, publish: Callable[[dict], None], on_audio: Callable[[np.ndarray, int, int], None] | None = None):
        self._publish = publish
        self._on_audio = on_audio
        self._stream: sd.InputStream | None = None
        self._lock = threading.RLock()
        self._label: str | None = None
        self._active_device_id: int | None = None
        self._sample_rate: int | None = None
        self._last_publish = 0.0

    def status(self) -> dict:
        return {"active": self._stream is not None, "label": self._label, "active_device_id": self._active_device_id}

    def start(self, device_id: int, label: str, language: str | None = None) -> dict:
        with self._lock:
            self.stop()
            validate_input(device_id)
            self._label = label
            errors: list[str] = []
            for candidate_id in input_candidates(device_id):
                candidate = sd.query_devices(candidate_id)
                stream = sd.InputStream(
                    device=candidate_id,
                    samplerate=int(candidate["default_samplerate"]),
                    channels=1,
                    dtype="float32",
                    blocksize=0,
                    callback=self._callback,
                    latency="low",
                )
                try:
                    stream.start()
                    self._stream = stream
                    self._active_device_id = candidate_id
                    self._sample_rate = int(candidate["default_samplerate"])
                    break
                except Exception as exc:
                    stream.close(ignore_errors=True)
                    errors.append(str(exc))
            if self._stream is None:
                self._label = None
                raise RuntimeError("Tidak ada jalur driver microphone yang dapat dibuka. " + " | ".join(errors))
            self._publish({"type": "mic.test.started", "label": label})
            return self.status()

    def stop(self) -> dict:
        with self._lock:
            if self._stream:
                try:
                    self._stream.stop(ignore_errors=True)
                    self._stream.close(ignore_errors=True)
                finally:
                    self._stream = None
            previous_label, self._label = self._label, None
            self._active_device_id = None
            self._sample_rate = None
            if previous_label:
                self._publish({"type": "mic.test.stopped", "label": previous_label})
            return self.status()

    def _callback(self, indata: np.ndarray, _frames: int, _time_info, status) -> None:
        if status:
            print(f"Mic test {self._label}: {status}")
        now = time.monotonic()
        if self._on_audio and self._label and self._sample_rate:
            self._on_audio(indata.copy(), int(time.time() * 1000), self._sample_rate)
        if now - self._last_publish < 0.08:
            return
        self._last_publish = now
        signal = indata[:, 0]
        rms = float(np.sqrt(np.mean(np.square(signal))))
        peak = float(np.max(np.abs(signal)))
        # A logarithmic scale keeps normal speaking levels visibly useful.
        level = max(0.0, min(1.0, (20 * np.log10(max(rms, 1e-6)) + 60) / 60))
        self._publish({"type": "mic.test.level", "label": self._label, "level": round(level, 3), "peak": round(peak, 3)})


class LiveMicTestManager:
    """A microphone level check with a temporary VAD and Whisper pipeline."""

    def __init__(self, settings: Settings, publish: Callable[[dict], None]):
        self._settings = settings
        self._publish = publish
        self._lock = threading.RLock()
        self._label: str | None = None
        self._segmenter: SpeechSegmenter | None = None
        self._stt: TranscriptionService | None = None
        self._tester = MicrophoneTester(publish, self._on_audio)

    def status(self) -> dict:
        return self._tester.status()

    def start(self, device_id: int, label: str, language: str | None = None) -> dict:
        with self._lock:
            self.stop()
            self._label = label
            test_settings = replace(self._settings, language=language or self._settings.language)
            self._stt = TranscriptionService(test_settings, self._on_final, self._on_error)
            self._segmenter = SpeechSegmenter(
                test_settings,
                lambda audio, start, end: self._stt and self._stt.submit(label, audio, start, end),
            )
            try:
                self._stt.start()
                self._segmenter.start()
                return self._tester.start(device_id, label)
            except Exception:
                self.stop()
                raise

    def stop(self) -> dict:
        with self._lock:
            self._tester.stop()
            if self._segmenter:
                self._segmenter.stop()
            if self._stt:
                self._stt.stop()
            self._segmenter = None
            self._stt = None
            self._label = None
            return self._tester.status()

    def _on_audio(self, block: np.ndarray, captured_at_ms: int, source_sample_rate: int) -> None:
        if self._segmenter:
            self._segmenter.push(block, captured_at_ms, source_sample_rate)

    def _on_final(self, speaker: str, text: str, started_at_ms: int, ended_at_ms: int) -> None:
        self._publish({
            "type": "mic.test.transcript", "label": speaker, "text": text,
            "started_at_ms": started_at_ms, "ended_at_ms": ended_at_ms,
        })

    def _on_error(self, speaker: str, error: str) -> None:
        self._publish({"type": "mic.test.error", "label": speaker, "error": error})
