from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import mlx_whisper

from book_sync.config import Settings
from book_sync.models import SegmentEntry, SegmentsFile
from book_sync.utils import format_timestamp


SAVE_INTERVAL = 50  # save every N segments
CHUNK_DURATION = 7200  # 2 hours per chunk (well within MLX int32 shape limit)


def load_segments_file(path: Path) -> SegmentsFile | None:
    if not path.exists():
        return None
    raw = json.loads(path.read_text())
    segments = [SegmentEntry(**s) for s in raw.get("segments", [])]
    return SegmentsFile(
        model=raw["model"],
        audio_file=raw["audio_file"],
        created_at=raw["created_at"],
        segments=segments,
    )


def save_segments_file(sf: SegmentsFile, path: Path) -> None:
    data = {
        "model": sf.model,
        "audio_file": sf.audio_file,
        "created_at": sf.created_at,
        "segments": [{"start": s.start, "end": s.end, "text": s.text} for s in sf.segments],
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.rename(path)


def _probe_duration(wav_path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(wav_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


def _extract_chunk(wav_path: Path, chunk_path: Path, start: float, duration: float) -> None:
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-t", str(duration),
        "-i", str(wav_path),
        "-c:a", "copy",
        str(chunk_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg chunk extraction failed:\n{result.stderr}")


def transcribe_audio(wav_path: Path, book_path: Path, settings: Settings) -> SegmentsFile:
    segments_path = book_path / "segments.json"

    existing = load_segments_file(segments_path)
    resume_offset = 0.0
    segments: list[SegmentEntry] = []

    if existing and existing.segments:
        segments = existing.segments
        resume_offset = segments[-1].end
        print(f"Resuming transcription from {format_timestamp(resume_offset)} ({len(segments)} segments)", flush=True)

    total_duration = _probe_duration(wav_path)
    print(f"Audio duration: {format_timestamp(total_duration)}", flush=True)
    print(f"Model: {settings.model}", flush=True)

    sf = SegmentsFile(
        model=settings.model,
        audio_file=wav_path.name,
        created_at=existing.created_at if existing else datetime.now(timezone.utc).isoformat(),
        segments=segments,
    )

    # Build chunk boundaries
    chunk_starts: list[float] = []
    t = 0.0
    while t < total_duration:
        chunk_starts.append(t)
        t += CHUNK_DURATION

    for chunk_idx, chunk_start in enumerate(chunk_starts):
        chunk_end = min(chunk_start + CHUNK_DURATION, total_duration)

        # Skip chunks fully covered by existing segments
        if chunk_end <= resume_offset:
            continue

        chunk_num = chunk_idx + 1
        total_chunks = len(chunk_starts)
        print(
            f"Chunk {chunk_num}/{total_chunks}: "
            f"{format_timestamp(chunk_start)} - {format_timestamp(chunk_end)}",
            flush=True,
        )

        # Extract chunk WAV
        chunk_path = book_path / f"_chunk_{chunk_idx}.wav"
        _extract_chunk(wav_path, chunk_path, chunk_start, CHUNK_DURATION)

        try:
            result = mlx_whisper.transcribe(
                str(chunk_path),
                path_or_hf_repo=settings.model,
                language="en",
                verbose=False,
            )
        finally:
            chunk_path.unlink(missing_ok=True)

        chunk_segments = result.get("segments", [])
        print(f"  Got {len(chunk_segments)} segments", flush=True)

        new_in_chunk = 0
        last_log = time.monotonic()
        for seg in chunk_segments:
            abs_start = chunk_start + seg["start"]
            abs_end = chunk_start + seg["end"]

            # Skip segments already covered by resume
            if abs_end <= resume_offset:
                continue

            entry = SegmentEntry(start=abs_start, end=abs_end, text=seg["text"].strip())
            sf.segments.append(entry)
            new_in_chunk += 1

            now = time.monotonic()
            if now - last_log >= 30:
                print(
                    f"  Processing: {new_in_chunk}/{len(chunk_segments)} "
                    f"({format_timestamp(abs_end)}/{format_timestamp(total_duration)})",
                    flush=True,
                )
                last_log = now

            if len(sf.segments) % SAVE_INTERVAL == 0:
                save_segments_file(sf, segments_path)

        # Save after each chunk
        save_segments_file(sf, segments_path)
        print(
            f"  Chunk done. Total segments so far: {len(sf.segments)}",
            flush=True,
        )

    save_segments_file(sf, segments_path)
    print(f"Transcription complete: {len(sf.segments)} total segments", flush=True)
    return sf


def write_transcript(sf: SegmentsFile, book_path: Path) -> Path:
    out = book_path / "transcript.txt"
    lines = []
    for seg in sf.segments:
        ts = format_timestamp(seg.start)
        lines.append(f"[{ts}] {seg.text}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Transcript written: {out} ({len(lines)} lines)")
    return out
