from __future__ import annotations

from pathlib import Path

import httpx


def download_audio(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    existing_size = dest.stat().st_size if dest.exists() else 0

    headers = {}
    if existing_size > 0:
        headers["Range"] = f"bytes={existing_size}-"
        print(f"Resuming download from byte {existing_size}")

    with httpx.stream("GET", url, headers=headers, follow_redirects=True, timeout=30.0) as resp:
        if resp.status_code == 416:
            print("Download already complete")
            return dest

        if resp.status_code == 200:
            # Server doesn't support range; restart
            if existing_size > 0:
                print("Server does not support range requests, restarting download")
            existing_size = 0
            mode = "wb"
        elif resp.status_code == 206:
            mode = "ab"
        else:
            resp.raise_for_status()
            mode = "wb"

        content_length = resp.headers.get("content-length")
        total = int(content_length) + existing_size if content_length else None

        downloaded = existing_size
        last_pct = -1
        with open(dest, mode) as f:
            for chunk in resp.iter_bytes(chunk_size=1 << 20):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = int(downloaded * 100 / total)
                    if pct != last_pct and pct % 5 == 0:
                        print(f"Downloading: {pct}% ({downloaded}/{total} bytes)")
                        last_pct = pct

    print(f"Download complete: {dest} ({downloaded} bytes)")
    return dest
