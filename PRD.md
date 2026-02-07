# PRD – Audiobook RSS → Timestamped Transcript (Step 1)

## 1. Overview

### 1.1 Goal

Build a tool that:

1. Accepts an **Audiobookshelf RSS feed URL** (public, no auth)
2. Downloads the audiobook audio file
3. Converts it to Whisper-compatible format
4. Transcribes it using **Whisper Large-v3-Turbo** (configurable)
5. Outputs a **plain text transcript with native segment timestamps**

Primary use case:

> User can run `grep "some phrase" transcript.txt` and get an approximate timestamp (±30 seconds).

### 1.2 Constraints

- No forced alignment
- No diarization
- No paragraph regrouping
- Use native Whisper segment timestamps
- Fully local processing
- Restartable/resumable
- Designed for later web UI (Step 2)

---

## 2. Inputs & Outputs

### 2.1 Input

- Public RSS feed (iTunes compatible) from Audiobookshelf
- Feed contains **one audio enclosure per book/episode**
- Audio format typically `.m4b` or `.mp3`

### 2.2 Final Output (required)

A single text file:

```
data/<Book Title>/transcript.txt
```

Format:

```
[HH:MM:SS] segment text...
[HH:MM:SS] next segment text...
```

Rules:

- One Whisper segment per line
- Timestamps derived directly from ASR output
- UTF-8 encoding
- No extra markup

---

## 3. Folder Structure (FLAT PER-BOOK)

### 3.1 Repository Layout

```
repo-root/
├── config/
│   └── settings.yaml
├── data/
│   └── <Book Title>/
│       ├── feed.json
│       ├── book.m4b
│       ├── book.wav
│       ├── segments.json
│       ├── transcript.txt
│       └── state.json
└── cli.py
```

### 3.2 Naming Rules

- `<Book Title>`
  - Sanitized from RSS title
  - Remove: `/ \ : * ? " < > |`
  - Trim to 120 characters
- Audio file names:
  - `book.m4b` (original download; extension may be `.mp3` depending on source)
  - `book.wav` (converted audio)

---

## 4. File Formats

### 4.1 `feed.json`

```json
{
  "title": "Book Title",
  "audio_url": "https://...",
  "duration_seconds": 129600,
  "rss_item": { "raw": "cached_rss_item_object_or_fields" }
}
```

### 4.2 `segments.json`

```json
{
  "model": "large-v3-turbo",
  "audio_file": "book.wav",
  "created_at": "2026-02-07T12:00:00Z",
  "segments": [
    { "start": 0.0, "end": 12.43, "text": "Call me Ishmael." },
    { "start": 12.43, "end": 18.92, "text": "Some years ago..." }
  ]
}
```

### 4.3 `transcript.txt` (REQUIRED OUTPUT)

Example:

```
[00:00:00] Call me Ishmael.
[00:00:12] Some years ago...
```

Rules:

- Timestamp = `floor(segment.start)`
- Format always `HH:MM:SS` (zero-padded)
- One segment per line
- No blank lines
- No additional metadata

### 4.4 `state.json`

```json
{
  "stage": "downloading | converting | transcribing | done",
  "last_segment": 1243,
  "model": "large-v3-turbo",
  "checksums": {
    "audio_original": "sha256...",
    "audio_wav": "sha256..."
  }
}
```

---

## 5. Functional Requirements

### 5.1 CLI Commands

#### Add & Process RSS

```bash
transcribe rss <feed_url>
```

Behavior:

1. Parse RSS
2. Create folder `data/<sanitized title>/`
3. Download audio
4. Convert
5. Transcribe
6. Write transcript

#### List Books

```bash
transcribe list
```

Output example:

```
Book Title – done
Another Book – transcribing
```

#### Process Existing

```bash
transcribe process "<Book Title>"
```

---

### 5.2 Feed Parsing

- Read RSS without auth
- Extract:
  - title
  - audio enclosure URL
  - duration (if present)
- Sanitize title per naming rules
- Persist `feed.json`

---

### 5.3 Downloading

- Direct HTTP GET
- Support resume via HTTP range requests
- Verify size if provided
- Save as:

```
data/<Book Title>/book.m4b
```

(If the enclosure is `.mp3`, still save as `book.mp3` or save as `book.m4b` only if you also convert; implementation choice, but must be consistent and reflected in `state.json` / `feed.json`.)

---

### 5.4 Audio Conversion

Use ffmpeg equivalent:

- Input: `book.m4b` or `book.mp3`
- Output: `book.wav`
- Parameters:
  - 16kHz sample rate
  - mono
  - PCM signed 16-bit (`pcm_s16le`)

Output:

```
data/<Book Title>/book.wav
```

---

### 5.5 Transcription

- Default model: `large-v3-turbo`
- Use segment timestamps
- Streaming/chunked decode (implementation-specific)
- Write to:

```
data/<Book Title>/segments.json
```

Must be restartable using `state.json`:

- If interrupted, rerun should continue (either from last known segment, or by detecting existing `segments.json` and skipping completed work).

---

### 5.6 Transcript Writing

Transform segments → txt:

Algorithm:

1. Load `segments.json`
2. For each segment:
   - `ts = floor(segment.start)`
   - Print: `"[HH:MM:SS] {text}"`

Save:

```
data/<Book Title>/transcript.txt
```

---

## 6. Non-Goals (Explicit)

- No forced alignment
- No word timestamps
- No speaker detection
- No paragraph formatting
- No search UI in Step 1
- No DRM handling

---

## 7. Performance Expectations

- Must handle ~36h audio
- Resume after crash/interruption
- Disk usage should be reasonable (goal: ≤ 2× source size, but WAV may temporarily exceed; acceptable if documented)
- Progress logging to stdout

---

## 8. Error Handling

### 8.1 Recoverable

- Network drop → resume download
- Transcription interrupted → resume from last segment
- ffmpeg failure → retry with clear error output

### 8.2 Fatal

- Invalid RSS
- No audio enclosure found
- Unsupported codec (ffmpeg cannot decode)
- Out of disk space

---

## 9. Configuration (`config/settings.yaml`)

```yaml
model: large-v3-turbo
ffmpeg_path: ffmpeg
sample_rate: 16000
device: auto
```

---

## 10. Step 2 Compatibility Requirements

Design must enable later:

- Load `segments.json` directly
- Build a search index without re-transcription
- Deep link to timestamps

Therefore:

- Do not modify raw segments after writing `segments.json`
- Preserve exact timestamps from ASR output
- Keep all files self-contained per book folder

---

## 11. Acceptance Criteria

1. User runs:

```bash
transcribe rss <url>
```

2. Result exists:

```
data/<Book>/transcript.txt
```

3. Command works:

```bash
grep "phrase" data/<Book>/transcript.txt
```

and shows timestamped lines.

4. Interrupt + rerun resumes and completes without restarting from scratch (where feasible).

---

# End of PRD (Step 1)
