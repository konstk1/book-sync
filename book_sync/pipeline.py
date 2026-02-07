from __future__ import annotations

import json
from pathlib import Path

from book_sync.config import Settings, DATA_DIR
from book_sync.convert import convert_to_wav
from book_sync.download import download_audio
from book_sync.feed import audio_extension, parse_feed, save_feed_json
from book_sync.models import State
from book_sync.transcribe import load_segments_file, transcribe_audio, write_transcript
from book_sync.utils import book_dir, sha256_file


def load_state(book_path: Path) -> State:
    path = book_path / "state.json"
    if path.exists():
        raw = json.loads(path.read_text())
        return State(**raw)
    return State()


def save_state(state: State, book_path: Path) -> None:
    path = book_path / "state.json"
    data = {
        "stage": state.stage,
        "last_segment": state.last_segment,
        "model": state.model,
        "checksums": state.checksums,
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.rename(path)


def run_rss(url: str, settings: Settings) -> None:
    print(f"Parsing RSS feed: {url}")
    info = parse_feed(url)
    print(f"Book: {info.title}")
    save_feed_json(info)

    bdir = book_dir(info.title)
    ext = audio_extension(info.audio_url)
    audio_path = bdir / f"book{ext}"
    wav_path = bdir / "book.wav"

    state = load_state(bdir)
    state.model = settings.model

    # Stage: downloading
    if state.stage == "downloading":
        download_audio(info.audio_url, audio_path)
        state.checksums["audio_original"] = sha256_file(audio_path)
        state.stage = "converting"
        save_state(state, bdir)

    # Stage: converting
    if state.stage == "converting":
        convert_to_wav(audio_path, wav_path, settings)
        state.checksums["audio_wav"] = sha256_file(wav_path)
        state.stage = "transcribing"
        save_state(state, bdir)

    # Stage: transcribing
    if state.stage == "transcribing":
        sf = transcribe_audio(wav_path, bdir, settings)
        state.last_segment = len(sf.segments)
        write_transcript(sf, bdir)
        state.stage = "done"
        save_state(state, bdir)

    print(f"Pipeline complete: {info.title}")


def run_process(title: str, settings: Settings) -> None:
    bdir = book_dir(title)
    if not bdir.exists():
        raise FileNotFoundError(f"Book directory not found: {bdir}")

    feed_path = bdir / "feed.json"
    if not feed_path.exists():
        raise FileNotFoundError(f"No feed.json in {bdir}")

    feed_data = json.loads(feed_path.read_text())
    ext = audio_extension(feed_data["audio_url"])
    audio_path = bdir / f"book{ext}"
    wav_path = bdir / "book.wav"

    state = load_state(bdir)
    state.model = settings.model

    if state.stage == "downloading":
        download_audio(feed_data["audio_url"], audio_path)
        state.checksums["audio_original"] = sha256_file(audio_path)
        state.stage = "converting"
        save_state(state, bdir)

    if state.stage == "converting":
        convert_to_wav(audio_path, wav_path, settings)
        state.checksums["audio_wav"] = sha256_file(wav_path)
        state.stage = "transcribing"
        save_state(state, bdir)

    if state.stage == "transcribing":
        sf = transcribe_audio(wav_path, bdir, settings)
        state.last_segment = len(sf.segments)
        write_transcript(sf, bdir)
        state.stage = "done"
        save_state(state, bdir)

    if state.stage == "done":
        print(f"Book already complete: {title}")


def list_books() -> list[tuple[str, str]]:
    if not DATA_DIR.exists():
        return []
    results = []
    for child in sorted(DATA_DIR.iterdir()):
        if child.is_dir():
            state = load_state(child)
            results.append((child.name, state.stage))
    return results
