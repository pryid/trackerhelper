from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from ..domain.dedupe import DedupeResult, TrackFingerprint, find_redundant_releases
from ..infra.fingerprint import iter_fingerprints
from ..infra.scan import iter_audio_files, release_root_for_path
from ..formatting.dedupe import dedupe_result_to_dict
from .dedupe_reporting import DedupeReportPaths, apply_actions, ensure_dir, print_summary, write_reports
from .progress import ProgressCallback


def _require_executable(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def validate_actions(
    *, delete: bool, move_to: Path | None, require_action: bool
) -> tuple[int, str | None]:
    if delete and move_to is not None:
        return 2, "ERROR: --delete and --move-to cannot be used together"
    if require_action and not delete and move_to is None:
        return 2, "ERROR: --apply-plan requires --move-to or --delete"
    return 0, None


def write_plan(result: DedupeResult, plan_path: Path, roots: list[Path], exts: set[str]) -> None:
    data = dedupe_result_to_dict(result, roots=roots, exts=exts)
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_plan(plan_path: Path) -> dict[str, Any]:
    return json.loads(plan_path.read_text(encoding="utf-8"))


def apply_plan(
    plan_path: Path,
    *,
    move_to: Path | None,
    delete: bool,
    quiet: bool,
) -> tuple[int, int, int]:
    code, err = validate_actions(delete=delete, move_to=move_to, require_action=True)
    if err:
        print(err)
        return code, 0, 0
    data = load_plan(plan_path)
    redundant = {Path(p) for p in data.get("redundant", [])}
    result = DedupeResult(
        redundant=redundant,
        duplicate_of={},
        contained_in={},
        unique_count={},
        sizes={},
        post_contained=[],
        unsafe=[],
    )
    moved, deleted_count = apply_actions(
        result,
        move_to=str(move_to) if move_to is not None else None,
        delete=delete,
        quiet=quiet,
    )
    return 0, moved, deleted_count


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
    plan_out: Path | None = None,
) -> tuple[int, DedupeResult | None, DedupeReportPaths | None]:
    if not _require_executable("fpcalc"):
        print("ERROR: 'fpcalc' not found in PATH. Install chromaprint (fpcalc).", flush=True)
        return 2, None, None

    code, err = validate_actions(delete=delete, move_to=move_to, require_action=False)
    if err:
        print(err, flush=True)
        return code, None, None

    ensure_dir(out_dir)

    audio_files = list(iter_audio_files(roots, exts))
    if not audio_files:
        print("No audio files found in the specified roots.", flush=True)
        return 1, None, None

    if not quiet:
        print(f"Audio files found: {len(audio_files)}")
        print(f"Computing fpcalc fingerprints (jobs={jobs})...")

    if progress is not None:
        progress.start(len(audio_files))

    tsv_path = out_dir / "discog_audiofp.tsv"
    release_keys: dict[Path, set[TrackFingerprint]] = {}
    fingerprint_count = 0

    with tsv_path.open("w", encoding="utf-8") as f:
        for row in iter_fingerprints(audio_files, jobs, on_progress=progress.advance if progress else None):
            fingerprint_count += 1
            f.write(f"{row.duration}\t{row.fingerprint}\t{row.path.as_posix()}\n")
            rel = release_root_for_path(row.path, roots)
            if rel is None:
                continue
            release_keys.setdefault(rel, set()).add(TrackFingerprint(row.duration, row.fingerprint))

    if progress is not None:
        progress.finish()

    if fingerprint_count == 0:
        print("fpcalc failed to process any files (check codecs/files).", flush=True)
        return 1, None, None

    result = find_redundant_releases(release_keys)
    paths = write_reports(result, out_dir)

    if plan_out is not None:
        write_plan(result, plan_out, roots, exts)

    if not quiet:
        print_summary(result, paths, out_dir)

    apply_actions(
        result,
        move_to=str(move_to) if move_to is not None else None,
        delete=delete,
        quiet=quiet,
    )

    return 0, result, paths


def default_jobs() -> int:
    return max(1, (os.cpu_count() or 2))
