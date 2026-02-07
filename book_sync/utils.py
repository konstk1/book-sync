from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path

from book_sync.config import DATA_DIR


def sanitize_title(title: str) -> str:
    cleaned = re.sub(r'[/\\:*?"<>|]', "", title).strip()
    return cleaned[:120]


def format_timestamp(seconds: float) -> str:
    total = int(math.floor(seconds))
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def book_dir(title: str) -> Path:
    return DATA_DIR / sanitize_title(title)
