from __future__ import annotations

import queue
import threading
from collections.abc import Callable

import numpy as np
import webrtcvad

from .config import Settings


class SpeechSegmenter:
    """Converts microphone blocks into speech-only 16 kHz utterances."""

    def __init__(self, settings: Settings, on_segment: Callable[[np.ndarray, int, int], None], on_partial: Callable[[np.ndarray, int, int], None] | None = None):
        self._settings = settings
        self._on_segment = on_segment
        self._on_partial = on_partial
        self._input: queue.Queue[tuple[np.ndarray, int, int]] = queue.Queue(maxsize=400)
        self._running = threading.Event()
        self._thread: threading.Thread | None = None
        self._dropped_blocks = 0

    def start(self) -> None:
        self._running.set()
        self._thread = threading.Thread(target=self._run, daemon=True, name="vad-segmenter")
        self._thread.start()

    def stop(self) -> None:
        self._running.clear()
        if self._thread:
            self._thread.join(timeout=2)

    def push(self, block: np.ndarray, captured_at_ms: int, source_sample_rate: int | None = None) -> None:
        try:
            self._input.put_nowait((block.copy(), captured_at_ms, source_sample_rate or self._settings.sample_rate))
        except queue.Full:
            self._dropped_blocks += 1

    def _run(self) -> None:
        vad = webrtcvad.Vad(self._settings.vad_aggressiveness)
        frame_samples = 320  # 20 ms at 16 kHz, accepted by WebRTC VAD.
        pcm_buffer = np.empty(0, dtype=np.int16)
        active: list[np.ndarray] = []
        started_at: int | None = None
        silence_frames = 0
        last_frame_end_ms = 0
        max_samples = int(self._settings.max_utterance_seconds * 16000)
        next_partial_samples = 16000
        min_samples = int(self._settings.min_utterance_ms * 16)

        while self._running.is_set() or not self._input.empty():
            try:
                block, captured_at_ms, source_sample_rate = self._input.get(timeout=0.1)
            except queue.Empty:
                continue
            mono = block[:, 0] if block.ndim == 2 else block
            # Device fallback drivers may use 44.1 kHz. Resample every block to the VAD's 16 kHz format.
            source_positions = np.arange(len(mono), dtype=np.float32)
            target_length = max(1, round(len(mono) * 16000 / source_sample_rate))
            target_positions = np.linspace(0, len(mono) - 1, target_length, dtype=np.float32)
            downsampled = np.interp(target_positions, source_positions, mono)
            pcm_buffer = np.concatenate((pcm_buffer, np.clip(downsampled * 32767, -32768, 32767).astype(np.int16)))

            while len(pcm_buffer) >= frame_samples:
                frame = pcm_buffer[:frame_samples]
                pcm_buffer = pcm_buffer[frame_samples:]
                is_speech = vad.is_speech(frame.tobytes(), 16000)
                frame_end_ms = captured_at_ms
                last_frame_end_ms = frame_end_ms
                if is_speech:
                    if started_at is None:
                        started_at = frame_end_ms - 20
                    active.append(frame)
                    silence_frames = 0
                    if self._on_partial and sum(len(item) for item in active) >= next_partial_samples:
                        preview = np.concatenate(active)
                        self._on_partial(preview.astype(np.float32) / 32768, started_at, frame_end_ms)
                        next_partial_samples += 16000
                elif active:
                    active.append(frame)
                    silence_frames += 1

                active_samples = sum(len(item) for item in active)
                should_finish = active and (
                    silence_frames * 20 >= self._settings.silence_ms or active_samples >= max_samples
                )
                if should_finish:
                    utterance = np.concatenate(active)
                    if len(utterance) >= min_samples and started_at is not None:
                        self._on_segment(utterance.astype(np.float32) / 32768, started_at, frame_end_ms)
                    active, started_at, silence_frames = [], None, 0
                    next_partial_samples = 16000

        # Preserve the last spoken phrase when a user stops the session before VAD sees silence.
        if active and started_at is not None:
            utterance = np.concatenate(active)
            if len(utterance) >= min_samples:
                self._on_segment(utterance.astype(np.float32) / 32768, started_at, last_frame_end_ms)
