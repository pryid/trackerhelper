from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .io.scan import iter_audio_files as _iter_audio_files


def iter_audio_files(roots: Iterable[Path], exts: set[str]):
    """Yield audio files from multiple root folders."""
    return _iter_audio_files(roots, exts)


def release_dir_from_path(p: Path) -> str | None:
    """
    Treat the first folder under Albums/ or Singles/ as the release.
    Example: Albums/Clams Casino - Moon Trip Radio - 2019/01 - ... ->
    Albums/Clams Casino - Moon Trip Radio - 2019
    """
    parts = list(p.parts)
    lower_parts = [part.lower() for part in parts]
    if "albums" in lower_parts:
        i = lower_parts.index("albums")
    elif "singles" in lower_parts:
        i = lower_parts.index("singles")
    else:
        return None
    if i + 1 >= len(parts):
        return None
    return str(Path(*parts[: i + 2]))
