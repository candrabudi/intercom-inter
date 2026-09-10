from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable

import numpy as np
import sounddevice as sd

from .config import Settings


class AudioRouter:
    """Routes two microphones to the opposite headset and mirrors blocks to STT."""

    def __init__(
        self,
        settings: Settings,
        mic_a: int,
        speaker_a: int,
        mic_b: int,
        speaker_b: int,
        on_audio: Callable[[str, np.ndarray, int], None],
    ):
        self._settings = settings
        self._on_audio = on_audio
        self._targets = {"A": self._new_queue(), "B": self._new_queue()}
        self._streams: list[sd.Stream] = []
        self._stopped = False
        self._lock = threading.Lock()
        self._device_pairs = (("A", mic_a, "B", speaker_b), ("B", mic_b, "A", speaker_a))

    @staticmethod
    def _new_queue() -> queue.Queue[np.ndarray]:
        return queue.Queue(maxsize=80)

    def start(self) -> None:
        try:
            for source, input_device, target, output_device in self._device_pairs:
                stream = sd.Stream(
                    device=(input_device, output_device),
                    samplerate=self._settings.sample_rate,
                    blocksize=self._settings.blocksize,
                    channels=self._settings.channels,
                    dtype="float32",
                    callback=self._callback(source, target),
                    latency="low",
                )
                stream.start()
                self._streams.append(stream)
        except Exception:
            self.stop()
            raise

    def stop(self) -> None:
        with self._lock:
            if self._stopped:
                return
            self._stopped = True
            for stream in self._streams:
                try:
                    stream.stop(ignore_errors=True)
                    stream.close(ignore_errors=True)
                except Exception:
                    pass
            self._streams.clear()

    def _callback(self, source: str, target: str):
        def callback(indata: np.ndarray, outdata: np.ndarray, _frames: int, _time_info, status) -> None:
            if status:
                print(f"Audio {source}->{target}: {status}")
            block = indata.copy()
            try:
                self._targets[target].put_nowait(block)
            except queue.Full:
                try:
                    self._targets[target].get_nowait()
                    self._targets[target].put_nowait(block)
                except queue.Empty:
                    pass
            self._on_audio(source, block, int(time.time() * 1000))
            try:
                outbound = self._targets[source].get_nowait()
                outdata[:] = outbound
            except queue.Empty:
                outdata.fill(0)

        return callback
