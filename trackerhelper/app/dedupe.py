from __future__ import annotations

import os
import shutil
from pathlib import Path

from ..domain.dedupe import build_release_keys, find_redundant_releases
from ..infra.fingerprint import fingerprint_files, fp_row_sort_key
from ..infra.scan import iter_audio_files, release_root_for_path
from .dedupe_reporting import apply_actions, ensure_dir, print_summary, write_reports
from .progress import ProgressCallback


def _require_executable(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def run_dedupe(
    *,
    roots: list[Path],
    exts: set[str],
    out_dir: Path,
    jobs: int,
    move_to: Path | None,
    delete: bool,
    quiet: bool,
    progress: ProgressCallback | None = None,
) -> int:
    if not _require_executable("fpcalc"):
        print("ERROR: 'fpcalc' not found in PATH. Install chromaprint (fpcalc).", flush=True)
        return 2

    if delete and move_to is not None:
        print("ERROR: --delete and --move-to cannot be used together", flush=True)
        return 2

    ensure_dir(out_dir)

    audio_files = list(iter_audio_files(roots, exts))
    if not audio_files:
        print("No audio files found in the specified roots.", flush=True)
        return 1

    if not quiet:
        print(f"Audio files found: {len(audio_files)}")
        print(f"Computing fpcalc fingerprints (jobs={jobs})...")

    if progress is not None:
        progress.start(len(audio_files))
    rows = fingerprint_files(audio_files, jobs, on_progress=progress.advance if progress else None)
    if progress is not None:
        progress.finish()
    if not rows:
        print("fpcalc failed to process any files (check codecs/files).", flush=True)
        return 1

    tsv_path = out_dir / "discog_audiofp.tsv"
    rows.sort(key=fp_row_sort_key)
    with tsv_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(f"{row.duration}\t{row.fingerprint}\t{row.path.as_posix()}\n")

    release_keys = build_release_keys(rows, lambda p: release_root_for_path(p, roots))
    result = find_redundant_releases(release_keys)
    paths = write_reports(result, out_dir)

    if not quiet:
        print_summary(result, paths, out_dir)

    apply_actions(
        result,
        move_to=str(move_to) if move_to is not None else None,
        delete=delete,
        quiet=quiet,
    )

    return 0


def default_jobs() -> int:
    return max(1, (os.cpu_count() or 2))
