from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ReleaseScan:
    path: Path
    audio_files: list[Path]


def iter_release_scans(
    root: Path,
    exts: set[str],
    include_root: bool,
) -> Iterable[ReleaseScan]:
    """Iterate folders and return audio files inside each folder."""
    for dirpath, _, filenames in os.walk(root):
        folder = Path(dirpath)
        if folder == root and not include_root:
            continue

        audio_files = [
            folder / fn
            for fn in filenames
            if Path(fn).suffix.lower() in exts
        ]

        if audio_files:
            audio_files.sort()
            yield ReleaseScan(path=folder, audio_files=audio_files)


def iter_audio_files(roots: Iterable[Path], exts: set[str]) -> Iterable[Path]:
    """Yield audio files under multiple roots."""
    for root in roots:
        if not root.exists():
            continue
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                p = Path(dirpath) / fn
                if p.is_file() and p.suffix.lower() in exts:
                    yield p


def release_root_for_path(path: Path, roots: Iterable[Path]) -> Path | None:
    """Return the release folder for a file under the given roots."""
    for root in roots:
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        if not rel.parts:
            return root
        return root / rel.parts[0]
    return None
