from __future__ import annotations

import re
import subprocess
from pathlib import Path

from book_sync.config import Settings


def _probe_duration(input_path: Path, ffmpeg_path: str) -> float | None:
    """Get duration in seconds via ffprobe."""
    cmd = [
        ffmpeg_path.replace("ffmpeg", "ffprobe"),
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(input_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())
    except (ValueError, FileNotFoundError):
        return None


def convert_to_wav(input_path: Path, output_path: Path, settings: Settings) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        print(f"WAV already exists: {output_path}")
        return output_path

    total_duration = _probe_duration(input_path, settings.ffmpeg_path)

    cmd = [
        settings.ffmpeg_path,
        "-i", str(input_path),
        "-ar", str(settings.sample_rate),
        "-ac", "1",
        "-c:a", "pcm_s16le",
        "-progress", "pipe:1",
        "-y",
        str(output_path),
    ]

    print(f"Converting: {input_path.name} -> {output_path.name}")
    if total_duration:
        print(f"Duration: {total_duration:.0f}s")

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    last_pct = -1
    for line in proc.stdout:
        m = re.match(r"out_time_ms=(\d+)", line)
        if m and total_duration:
            current = int(m.group(1)) / 1_000_000
            pct = min(int(current * 100 / total_duration), 100)
            if pct != last_pct and pct % 5 == 0:
                print(f"Converting: {pct}%")
                last_pct = pct

    proc.wait()
    if proc.returncode != 0:
        stderr = proc.stderr.read()
        raise RuntimeError(f"ffmpeg failed (exit {proc.returncode}):\n{stderr}")

    print(f"Conversion complete: {output_path}")
    return output_path
