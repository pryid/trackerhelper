from __future__ import annotations

import re
from pathlib import Path

_TRACK_NUM_RE = re.compile(r"^\s*(\d{1,3})\s*([.\-_\s]+)\s*(.*)$")


def build_tracklist_lines(audio_files: list[Path], *, sort: bool = True) -> list[str]:
    """
    Builds a tracklist from file names.

    Logic is unchanged:
    - If the name starts with a track number, keep it.
    - Otherwise, auto-number starting at 01.
    """
    lines: list[str] = []
    auto_n = 1

    files = sorted(audio_files) if sort else audio_files
    for f in files:
        stem = f.stem
        m = _TRACK_NUM_RE.match(stem)
        if m:
            num = m.group(1)
            title = m.group(3).strip() or stem
            width = 3 if len(num) >= 3 else 2
            num_fmt = f"{int(num):0{width}d}"
        else:
            num_fmt = f"{auto_n:02d}"
            title = stem.strip() or stem
            auto_n += 1

        title = re.sub(r"\s+", " ", title).strip()
        lines.append(f"{num_fmt}. {title}")

    return lines
