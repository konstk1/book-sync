from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

import feedparser

from book_sync.models import FeedInfo
from book_sync.utils import book_dir


def parse_feed(url: str) -> FeedInfo:
    feed = feedparser.parse(url)
    if feed.bozo and not feed.entries:
        raise ValueError(f"Failed to parse RSS feed: {feed.bozo_exception}")

    title = feed.feed.get("title", "Untitled")

    audio_url = None
    duration_seconds = None
    rss_item = {}

    for entry in feed.entries:
        for link in entry.get("links", []):
            if link.get("rel") == "enclosure" or link.get("type", "").startswith("audio/"):
                audio_url = link["href"]
                rss_item = {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                }
                break
        if audio_url:
            break

    if not audio_url:
        # Fall back: check enclosures directly
        for entry in feed.entries:
            for enc in entry.get("enclosures", []):
                audio_url = enc.get("href") or enc.get("url")
                if audio_url:
                    rss_item = {
                        "title": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                    }
                    break
            if audio_url:
                break

    if not audio_url:
        raise ValueError("No audio enclosure found in RSS feed")

    # Try to get duration from itunes:duration
    for entry in feed.entries:
        dur = entry.get("itunes_duration")
        if dur:
            duration_seconds = _parse_duration(dur)
            break

    return FeedInfo(
        title=title,
        audio_url=audio_url,
        duration_seconds=duration_seconds,
        rss_item=rss_item,
    )


def _parse_duration(raw: str) -> float | None:
    try:
        parts = raw.split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(raw)
    except (ValueError, TypeError):
        return None


def audio_extension(url: str) -> str:
    path = urlparse(url).path
    ext = Path(path).suffix.lower()
    if ext in (".m4b", ".m4a", ".mp3", ".mp4", ".ogg", ".opus", ".wav"):
        return ext
    return ".m4b"


def save_feed_json(info: FeedInfo) -> Path:
    bdir = book_dir(info.title)
    bdir.mkdir(parents=True, exist_ok=True)
    out = bdir / "feed.json"
    data = {
        "title": info.title,
        "audio_url": info.audio_url,
        "duration_seconds": info.duration_seconds,
        "rss_item": info.rss_item,
    }
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.rename(out)
    print(f"Saved feed info: {out}")
    return out
