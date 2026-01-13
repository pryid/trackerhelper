from __future__ import annotations

import logging
from pathlib import Path

from ..domain.models import Release, StatsSummary, Track
from ..domain.utils import extract_years_from_text
from ..infra.ffprobe import AudioInfoReader
from ..infra.scan import iter_release_scans
from .progress import ProgressCallback
from .synthetic_dataset import load_synthetic_cases, make_track_paths

logger = logging.getLogger(__name__)


def collect_stats(
    root: Path,
    exts: set[str],
    include_root: bool,
    audio_reader: AudioInfoReader,
    progress: ProgressCallback | None = None,
) -> tuple[list[Release], StatsSummary]:
    """Collect stats from the filesystem plus ffprobe."""
    releases: list[Release] = []
    summary = StatsSummary(
        total_seconds=0.0,
        total_tracks=0,
        total_sr=set(),
        total_bit=set(),
        total_exts=set(),
        all_years=[],
    )

    scans = list(iter_release_scans(root, exts, include_root))
    total_files = sum(len(scan.audio_files) for scan in scans)
    if progress is not None:
        progress.start(total_files)

    for scan in scans:
        folder = scan.path
        audio_files = scan.audio_files
        folder_sum = 0.0
        folder_tracks = 0
        sr_set: set[int] = set()
        bit_set: set[int] = set()
        ext_set: set[str] = set()
        tracks: list[Track] = []

        for f in audio_files:
            dur, sr, bit = audio_reader.get_audio_info(f)
            if progress is not None:
                progress.advance()
            tracks.append(
                Track(
                    path=f,
                    duration_seconds=dur,
                    sample_rate=sr,
                    bit_depth=bit,
                )
            )
            if dur is None:
                logger.warning("Warning: can't read duration: %s", f)
                continue

            folder_sum += dur
            folder_tracks += 1

            if sr is not None:
                sr_set.add(sr)
            if bit is not None:
                bit_set.add(bit)
            ext_set.add(f.suffix.lower())

        if folder_tracks > 0:
            releases.append(
                Release(
                    path=folder,
                    duration_seconds=folder_sum,
                    track_count=folder_tracks,
                    sample_rates=sr_set,
                    bit_depths=bit_set,
                    exts=ext_set,
                    tracks=tracks,
                )
            )

            summary.total_seconds += folder_sum
            summary.total_tracks += folder_tracks
            summary.total_sr.update(sr_set)
            summary.total_bit.update(bit_set)
            summary.total_exts.update(ext_set)

            rel = folder.relative_to(root)
            summary.all_years.extend(extract_years_from_text(rel.as_posix()))

    if progress is not None:
        progress.finish()

    return releases, summary


def collect_synthetic_stats(root: Path) -> tuple[list[Release], StatsSummary]:
    """Synthetic dataset to test formatting without ffprobe or filesystem access."""
    releases: list[Release] = []
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
        tracks = [Track(path=p) for p in audio_files]

        releases.append(
            Release(
                path=folder,
                duration_seconds=secs,
                track_count=len(audio_files),
                sample_rates={sr},
                bit_depths={bit},
                exts={ext},
                tracks=tracks,
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
