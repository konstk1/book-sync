# AGENTS.md

Project guidelines and coding instructions for AI agents working in this repository. Product requirements are in [PRD.md](./PRD.md).

## Project Summary

book-sync is a Python CLI tool that converts Audiobookshelf RSS feeds into searchable, timestamped plain-text transcripts using Whisper. Fully local processing, no cloud APIs.

## Prerequisites

- Python
- ffmpeg (system install)
- Whisper model: `large-v3-turbo` (default, configurable in `config/settings.yaml`)

## Architecture

Entry point is `cli.py`. Configuration in `config/settings.yaml`.

Each book is self-contained under `data/<Book Title>/` with intermediate artifacts (`feed.json`, audio files, `segments.json`, `state.json`) and final output (`transcript.txt`).

The processing pipeline has discrete stages tracked by `state.json`: download → convert → transcribe → done. Each stage must be idempotent so that interrupted runs can resume without restarting from scratch.

## Coding Guidelines

- **Refer to PRD.md** for all product requirements, file formats, CLI commands, and acceptance criteria. Do not duplicate requirements here.
- **Resumability over correctness shortcuts** — every stage must be safely re-runnable. Use `state.json` to track progress and skip completed work.
- **`segments.json` is immutable once written** — Step 2 will build a search index directly from it. Never modify raw ASR output after persisting.
- **Keep book folders self-contained** — all artifacts for a book live in its own `data/<Title>/` directory. No cross-book references or shared state.
- **Progress logging to stdout** — the tool handles long-running operations (36+ hour audiobooks). Always provide visible progress output.
