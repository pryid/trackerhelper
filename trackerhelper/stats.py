from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable

from .ffprobe_utils import FfprobeClient
from .models import ReleaseStats, StatsSummary
from .utils import extract_years_from_text


def iter_release_audio_files(root: Path, exts: set[str], include_root: bool) -> Iterable[tuple[Path, list[Path]]]:
    """
    Iterate folders and return audio files inside each folder.

    Note:
    - In the release command, the tracklist is built from the files found in the folder,
      even if ffprobe could not read duration for some files (matches original behavior).
    """
    for dirpath, _, filenames in os.walk(root):
        folder = Path(dirpath)
        if folder == root and not include_root:
            continue

        audio_files: list[Path] = []
        for fn in filenames:
            p = folder / fn
            if p.is_file() and p.suffix.lower() in exts:
                audio_files.append(p)

        if audio_files:
            yield folder, sorted(audio_files)


def collect_real_stats(
    root: Path,
    exts: set[str],
    include_root: bool,
    ffprobe: FfprobeClient,
) -> tuple[list[ReleaseStats], StatsSummary]:
    """
    Collect stats from the real filesystem plus ffprobe.
    """
    releases: list[ReleaseStats] = []
    summary = StatsSummary(
        total_seconds=0.0,
        total_tracks=0,
        total_sr=set(),
        total_bit=set(),
        total_exts=set(),
        all_years=[],
    )

    for folder, audio_files in iter_release_audio_files(root, exts, include_root):
        folder_sum = 0.0
        folder_tracks = 0
        sr_set: set[int] = set()
        bit_set: set[int] = set()
        ext_set: set[str] = set()

        for f in audio_files:
            dur, sr, bit = ffprobe.get_audio_info(f)
            if dur is None:
                print(f"Warning: can't read duration: {f}", file=sys.stderr)
                continue

            folder_sum += dur
            folder_tracks += 1

            if sr is not None:
                sr_set.add(sr)
                summary.total_sr.add(sr)
            if bit is not None:
                bit_set.add(bit)
                summary.total_bit.add(bit)

            ext_set.add(f.suffix.lower())
            summary.total_exts.add(f.suffix.lower())

        if folder_tracks > 0:
            releases.append(
                ReleaseStats(
                    path=folder,
                    duration_seconds=folder_sum,
                    track_count=folder_tracks,
                    sample_rates=sr_set,
                    bit_depths=bit_set,
                    exts=ext_set,
                    audio_files=audio_files,
                )
            )

            summary.total_seconds += folder_sum
            summary.total_tracks += folder_tracks

            rel = folder.relative_to(root)
            summary.all_years.extend(extract_years_from_text(rel.as_posix()))

    return releases, summary


def collect_synthetic_stats(root: Path) -> tuple[list[ReleaseStats], StatsSummary]:
    """
    Synthetic dataset to test formatting without ffprobe or filesystem access.
    Data lives in synthetic_dataset.py.
    """
    from .synthetic_dataset import load_synthetic_cases, make_track_paths

    releases: list[ReleaseStats] = []
    summary = StatsSummary(
        total_seconds=0.0,
        total_tracks=0,
        total_sr=set(),
        total_bit=set(),
        total_exts=set(),
        all_years=[],
    )

    for case in load_synthetic_cases():
        g = case["group"]
        folder_name = case["folder_name"]
        secs = float(case["seconds"])
        sr = int(case["sample_rate"])
        bit = int(case["bit_depth"])
        ext = str(case["ext"])
        track_titles = list(case["track_titles"])
        dr_text = str(case["dr_text"])

        folder = root / g / folder_name
        audio_files = make_track_paths(folder, ext, track_titles)

        releases.append(
            ReleaseStats(
                path=folder,
                duration_seconds=secs,
                track_count=len(audio_files),
                sample_rates={sr},
                bit_depths={bit},
                exts={ext},
                audio_files=audio_files,
                dr_text=dr_text,
            )
        )

        summary.total_seconds += secs
        summary.total_tracks += len(audio_files)
        summary.total_sr.add(sr)
        summary.total_bit.add(bit)
        summary.total_exts.add(ext)

        rel = folder.relative_to(root)
        summary.all_years.extend(extract_years_from_text(rel.as_posix()))

    return releases, summary
