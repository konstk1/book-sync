from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from faster_whisper import WhisperModel

from book_sync.config import Settings
from book_sync.models import SegmentEntry, SegmentsFile


SAVE_INTERVAL = 50  # save every N segments


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


def transcribe_audio(wav_path: Path, book_path: Path, settings: Settings) -> SegmentsFile:
    segments_path = book_path / "segments.json"

    existing = load_segments_file(segments_path)
    resume_offset = 0.0
    segments: list[SegmentEntry] = []

    if existing and existing.segments:
        segments = existing.segments
        resume_offset = segments[-1].end
        print(f"Resuming transcription from {resume_offset:.2f}s ({len(segments)} segments)")

    print(f"Loading model: {settings.model} (device={settings.device})")
    model = WhisperModel(settings.model, device=settings.device)

    transcribe_kwargs: dict = {
        "language": "en",
        "vad_filter": True,
    }
    if resume_offset > 0:
        transcribe_kwargs["clip_timestamps"] = [resume_offset]

    print(f"Transcribing: {wav_path.name}")
    result_segments, info = model.transcribe(str(wav_path), **transcribe_kwargs)

    sf = SegmentsFile(
        model=settings.model,
        audio_file=wav_path.name,
        created_at=existing.created_at if existing else datetime.now(timezone.utc).isoformat(),
        segments=segments,
    )

    new_count = 0
    for seg in result_segments:
        entry = SegmentEntry(start=seg.start, end=seg.end, text=seg.text.strip())
        sf.segments.append(entry)
        new_count += 1

        if new_count % SAVE_INTERVAL == 0:
            save_segments_file(sf, segments_path)
            total = len(sf.segments)
            print(f"Progress: {total} segments, latest at {entry.end:.1f}s")

    # Final save
    save_segments_file(sf, segments_path)
    print(f"Transcription complete: {len(sf.segments)} total segments")
    return sf


def write_transcript(sf: SegmentsFile, book_path: Path) -> Path:
    from book_sync.utils import format_timestamp

    out = book_path / "transcript.txt"
    lines = []
    for seg in sf.segments:
        ts = format_timestamp(seg.start)
        lines.append(f"[{ts}] {seg.text}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Transcript written: {out} ({len(lines)} lines)")
    return out
