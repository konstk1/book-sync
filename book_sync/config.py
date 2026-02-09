from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULTS = {
    "model": "mlx-community/whisper-large-v3-turbo",
    "ffmpeg_path": "ffmpeg",
    "sample_rate": 16000,
}

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "settings.yaml"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass
class Settings:
    model: str = DEFAULTS["model"]
    ffmpeg_path: str = DEFAULTS["ffmpeg_path"]
    sample_rate: int = DEFAULTS["sample_rate"]


def load_settings(path: Path | None = None) -> Settings:
    path = path or CONFIG_PATH
    if path.exists():
        raw = yaml.safe_load(path.read_text()) or {}
        merged = {**DEFAULTS, **raw}
        return Settings(**{k: merged[k] for k in DEFAULTS})
    return Settings()
