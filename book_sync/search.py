from __future__ import annotations

from bisect import bisect_right
from pathlib import Path

from book_sync.models import SegmentEntry
from book_sync.transcribe import load_segments_file
from book_sync.utils import format_timestamp


CONTEXT_SEGMENTS = 2


def search_book(book_path: Path, query: str) -> list[dict]:
    """Search transcript for a phrase, returning matches with timestamps."""
    sf = load_segments_file(book_path / "segments.json")
    if sf is None:
        raise FileNotFoundError(f"No segments.json in {book_path}")

    segments = sf.segments
    if not segments:
        return []

    # Build joined text and offset index
    texts = [s.text.strip() for s in segments]
    offsets: list[int] = []  # start char offset per segment
    pos = 0
    for t in texts:
        offsets.append(pos)
        pos += len(t) + 1  # +1 for the space join

    joined = " ".join(texts)
    joined_lower = joined.lower()
    query_lower = query.lower()

    # Find all matches
    results = []
    start = 0
    while True:
        idx = joined_lower.find(query_lower, start)
        if idx == -1:
            break

        # Map char position to segment index
        seg_idx = bisect_right(offsets, idx) - 1

        # Find end segment
        end_char = idx + len(query_lower)
        seg_end_idx = bisect_right(offsets, end_char - 1) - 1

        # Build context window
        ctx_start = max(0, seg_idx - CONTEXT_SEGMENTS)
        ctx_end = min(len(segments) - 1, seg_end_idx + CONTEXT_SEGMENTS)

        results.append({
            "timestamp_start": segments[seg_idx].start,
            "timestamp_end": segments[seg_end_idx].end,
            "seg_start": seg_idx,
            "seg_end": seg_end_idx,
            "context": segments[ctx_start : ctx_end + 1],
            "context_start": ctx_start,
            "match_start": seg_idx,
            "match_end": seg_end_idx,
        })

        start = idx + 1

    return results


def print_results(query: str, results: list[dict]) -> None:
    if not results:
        print(f"No matches found for: {query!r}")
        return

    print(f"{len(results)} match(es) for: {query!r}\n")
    for i, r in enumerate(results, 1):
        ts_start = format_timestamp(r["timestamp_start"])
        ts_end = format_timestamp(r["timestamp_end"])
        print(f"── Match {i} [{ts_start} → {ts_end}] ──")
        for seg in r["context"]:
            marker = "  "
            ts = format_timestamp(seg.start)
            print(f"{marker}[{ts}] {seg.text.strip()}")
        print()
