from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    profile: str = os.getenv("STT_PROFILE", "standard")
    model_name: str = os.getenv("STT_MODEL", "small")
    # Empty means Whisper detects Indonesian, English, or mixed speech automatically.
    language: str | None = os.getenv("STT_LANGUAGE", "").strip() or None
    compute_type: str = os.getenv("STT_COMPUTE_TYPE", "int8")
    sample_rate: int = int(os.getenv("STT_AUDIO_SAMPLE_RATE", "48000"))
    blocksize: int = int(os.getenv("STT_AUDIO_BLOCKSIZE", "960"))
    channels: int = 1
    vad_aggressiveness: int = 2
    silence_ms: int = 700
    max_utterance_seconds: float = 14.0
    min_utterance_ms: int = 300
    llm_enabled: bool = os.getenv("LLM_ENABLED", "false").lower() == "true"
    llm_model: str = os.getenv("LLM_MODEL", "")

    @property
    def model_dir(self) -> Path:
        return ROOT_DIR / "models" / "faster-whisper"

    @property
    def sessions_dir(self) -> Path:
        return ROOT_DIR / "storage" / "sessions"

    @property
    def frontend_dir(self) -> Path:
        return ROOT_DIR / "frontend"


settings = Settings()
