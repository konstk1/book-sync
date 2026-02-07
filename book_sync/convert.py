from __future__ import annotations

import subprocess
from pathlib import Path

from book_sync.config import Settings


def convert_to_wav(input_path: Path, output_path: Path, settings: Settings) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        print(f"WAV already exists: {output_path}")
        return output_path

    cmd = [
        settings.ffmpeg_path,
        "-i", str(input_path),
        "-ar", str(settings.sample_rate),
        "-ac", "1",
        "-c:a", "pcm_s16le",
        "-y",
        str(output_path),
    ]

    print(f"Converting: {input_path.name} -> {output_path.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed (exit {result.returncode}):\n{result.stderr}")

    print(f"Conversion complete: {output_path}")
    return output_path
