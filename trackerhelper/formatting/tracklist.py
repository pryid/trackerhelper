from __future__ import annotations

import re
from pathlib import Path

_TRACK_NUM_RE = re.compile(r"^\s*(\d{1,3})\s*([.\-_\s]+)\s*(.*)$")


def _parse_track_num(path: Path) -> int | None:
    match = _TRACK_NUM_RE.match(path.stem)
    if not match:
        return None
    return int(match.group(1))


def _track_sort_key(path: Path) -> tuple[int, int, str]:
    track_num = _parse_track_num(path)
    if track_num is not None:
        return (0, track_num, path.name.lower())
    return (1, 10**9, path.name.lower())


def build_tracklist_lines(audio_files: list[Path], *, sort: bool = True) -> list[str]:
    """
    Builds a tracklist from file names.

    Logic is unchanged:
    - If the name starts with a track number, keep it.
    - Otherwise, auto-number starting at 01.
    """
    lines: list[str] = []
    auto_n = 1
    used_numbers: set[int] = set()

    files = sorted(audio_files, key=_track_sort_key) if sort else audio_files
    for f in files:
        stem = f.stem
        m = _TRACK_NUM_RE.match(stem)
        if m:
            num = m.group(1)
            num_int = int(num)
            title = m.group(3).strip() or stem
            width = 3 if len(num) >= 3 else 2
            num_fmt = f"{num_int:0{width}d}"
            used_numbers.add(num_int)
            auto_n = max(auto_n, num_int + 1)
        else:
            while auto_n in used_numbers:
                auto_n += 1
            num_fmt = f"{auto_n:02d}"
            title = stem.strip() or stem
            used_numbers.add(auto_n)
            auto_n += 1

        title = re.sub(r"\s+", " ", title).strip()
        lines.append(f"{num_fmt}. {title}")

    return lines
