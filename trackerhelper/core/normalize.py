from __future__ import annotations

import logging
import re
from pathlib import Path

from ..io.ffprobe_utils import FfprobeClient
from ..io.scan import ReleaseScan, iter_release_audio_files
from .tags import release_metadata_from_tags
from .utils import clean_name_part

_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")
logger = logging.getLogger(__name__)


def parse_year_from_folder_name(name: str) -> int | None:
    """Extract the last 4-digit year from a folder name."""
    years = [int(m.group(1)) for m in _YEAR_RE.finditer(name)]
    return years[-1] if years else None


def build_normalized_name(
    artist: str | None,
    album: str | None,
    year: int | None,
    single_mode: bool,
) -> str | None:
    """Build the normalized release folder name or return None if data is missing."""
    if not artist or not album or year is None:
        return None
    if single_mode:
        return clean_name_part(f"{artist} - {album} ({year})")
    return clean_name_part(f"{year} - {artist} - {album}")


def release_data_sort_key(item: ReleaseScan) -> str:
    """Sort key for release data by full path."""
    return item.path.as_posix().lower()


def normalize_release_folders(root: Path, exts: set[str], apply: bool) -> int:
    """Print or apply rename actions for release folders."""
    ffprobe = FfprobeClient()
    release_data = list(iter_release_audio_files(root, exts, include_root=True))
    release_data.sort(key=release_data_sort_key)

    if not release_data:
        print("No audio files found for normalization.")
        return 0

    single_mode = len(release_data) == 1
    if not single_mode:
        release_data = [item for item in release_data if item.path != root]
        if not release_data:
            single_mode = True
            release_data = [ReleaseScan(path=root, audio_files=[])]

    actions: list[tuple[Path, Path]] = []
    planned_targets: set[Path] = set()

    def display_path(p: Path) -> str:
        if p == root or p.parent == root.parent:
            return p.name
        try:
            rel = p.relative_to(root)
        except ValueError:
            return p.as_posix()
        return p.name if str(rel) == "." else rel.as_posix()

    for item in release_data:
        folder = item.path
        artist, album = release_metadata_from_tags(item.audio_files, ffprobe)
        year = parse_year_from_folder_name(folder.name)
        new_name = build_normalized_name(artist, album, year, single_mode)

        if not new_name:
            logger.warning("Skip: can't normalize '%s' (missing tags/year).", folder.name)
            continue

        target = folder.with_name(new_name)
        if target == folder:
            continue

        if target in planned_targets:
            logger.warning("Skip: duplicate target '%s'.", target.name)
            continue

        if target.exists() and target != folder:
            logger.warning("Skip: target exists '%s'.", target)
            continue

        planned_targets.add(target)
        actions.append((folder, target))

    if not actions:
        print("Nothing to normalize.")
        return 0

    if not apply:
        print("Dry run (use --apply/--y to apply):")
        for src, dst in actions:
            print(f"  {display_path(src)} -> {display_path(dst)}")
        return len(actions)

    for src, dst in actions:
        src.rename(dst)
        print(f"Renamed: {display_path(src)} -> {display_path(dst)}")

    return len(actions)
