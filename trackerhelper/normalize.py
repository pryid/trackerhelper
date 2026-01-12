from __future__ import annotations

import re
import sys
from pathlib import Path

from .ffprobe_utils import FfprobeClient
from .stats import iter_release_audio_files
from .tags import release_metadata_from_tags
from .utils import clean_name_part

_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")


def parse_year_from_folder_name(name: str) -> int | None:
    years = [int(m.group(1)) for m in _YEAR_RE.finditer(name)]
    return years[-1] if years else None


def build_normalized_name(
    artist: str | None,
    album: str | None,
    year: int | None,
    single_mode: bool,
) -> str | None:
    if not artist or not album or year is None:
        return None
    if single_mode:
        return clean_name_part(f"{artist} - {album} ({year})")
    return clean_name_part(f"{year} - {artist} - {album}")


def normalize_release_folders(root: Path, exts: set[str], apply: bool) -> int:
    ffprobe = FfprobeClient()
    release_data = [
        (folder, files)
        for folder, files in iter_release_audio_files(root, exts, include_root=True)
    ]
    release_data.sort(key=lambda x: x[0].as_posix().lower())

    if not release_data:
        print("No audio files found for normalization.")
        return 0

    single_mode = len(release_data) == 1
    if not single_mode:
        release_data = [(f, files) for f, files in release_data if f != root]
        if not release_data:
            single_mode = True
            release_data = [(root, [])]

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

    for folder, files in release_data:
        artist, album = release_metadata_from_tags(files, ffprobe)
        year = parse_year_from_folder_name(folder.name)
        new_name = build_normalized_name(artist, album, year, single_mode)

        if not new_name:
            print(
                f"Skip: can't normalize '{folder.name}' (missing tags/year).",
                file=sys.stderr,
            )
            continue

        target = folder.with_name(new_name)
        if target == folder:
            continue

        if target in planned_targets:
            print(f"Skip: duplicate target '{target.name}'.", file=sys.stderr)
            continue

        if target.exists() and target != folder:
            print(f"Skip: target exists '{target}'.", file=sys.stderr)
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
