from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FeedInfo:
    title: str
    audio_url: str
    duration_seconds: float | None = None
    rss_item: dict = field(default_factory=dict)


@dataclass
class State:
    stage: str = "downloading"
    last_segment: int = 0
    model: str = "large-v3-turbo"
    checksums: dict[str, str] = field(default_factory=dict)


@dataclass
class SegmentEntry:
    start: float
    end: float
    text: str


@dataclass
class SegmentsFile:
    model: str
    audio_file: str
    created_at: str
    segments: list[SegmentEntry] = field(default_factory=list)
