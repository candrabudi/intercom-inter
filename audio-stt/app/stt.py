from __future__ import annotations

import queue
import threading
from collections.abc import Callable

import numpy as np
from faster_whisper import WhisperModel

from .config import Settings


class TranscriptionService:
    """One shared Whisper model with independent speaker queues."""

    def __init__(self, settings: Settings, on_final: Callable[[str, str, int, int], None]):
        self._settings = settings
        self._on_final = on_final
        self._model: WhisperModel | None = None
        self._model_lock = threading.Lock()
        self._queues: dict[str, queue.Queue[tuple[np.ndarray, int, int]]] = {
            "A": queue.Queue(maxsize=30),
            "B": queue.Queue(maxsize=30),
        }
        self._running = threading.Event()
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        self._settings.model_dir.mkdir(parents=True, exist_ok=True)
        self._model = WhisperModel(
            self._settings.model_name,
            device="cpu",
            compute_type=self._settings.compute_type,
            download_root=str(self._settings.model_dir),
        )
        self._running.set()
        self._threads = [
            threading.Thread(target=self._run, args=(speaker,), daemon=True, name=f"stt-{speaker}")
            for speaker in ("A", "B")
        ]
        for thread in self._threads:
            thread.start()

    def stop(self) -> None:
        self._running.clear()
        for thread in self._threads:
            thread.join(timeout=5)

    def submit(self, speaker: str, audio: np.ndarray, started_at_ms: int, ended_at_ms: int) -> None:
        try:
            self._queues[speaker].put_nowait((audio, started_at_ms, ended_at_ms))
        except queue.Full:
            # Prefer live conversation over stale transcription work.
            pass

    def _run(self, speaker: str) -> None:
        while self._running.is_set() or not self._queues[speaker].empty():
            try:
                audio, started_at_ms, ended_at_ms = self._queues[speaker].get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                # CTranslate2 model access is serialized to keep CPU/RAM predictable on this laptop.
                with self._model_lock:
                    assert self._model is not None
                    segments, _ = self._model.transcribe(
                        audio,
                        language=self._settings.language,
                        vad_filter=False,
                        beam_size=5,
                        condition_on_previous_text=False,
                    )
                    text = " ".join(segment.text.strip() for segment in segments).strip()
                if text:
                    self._on_final(speaker, text, started_at_ms, ended_at_ms)
            except Exception as exc:  # Do not terminate a live session on one bad audio segment.
                print(f"STT {speaker} error: {exc}")
