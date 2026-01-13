from __future__ import annotations

import subprocess
from multiprocessing import Pool
from pathlib import Path
from typing import Callable, Iterable

from ..domain.dedupe import FingerprintRow


def fpcalc_one(path: Path) -> FingerprintRow | None:
    """
    Return FingerprintRow or None if fpcalc fails.
    """
    try:
        res = subprocess.run(
            ["fpcalc", "--", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return None

    if res.returncode != 0 or not res.stdout:
        return None

    dur = ""
    fp = ""
    for line in res.stdout.splitlines():
        if line.startswith("DURATION="):
            dur = line.split("=", 1)[1].strip()
        elif line.startswith("FINGERPRINT="):
            fp = line.split("=", 1)[1].strip()

    if not dur or not fp:
        return None

    return FingerprintRow(duration=dur, fingerprint=fp, path=path)


def fingerprint_files(
    audio_files: Iterable[Path],
    jobs: int,
    on_progress: Callable[[int], None] | None = None,
) -> list[FingerprintRow]:
    """Fingerprint files in parallel using fpcalc."""
    rows: list[FingerprintRow] = []
    with Pool(processes=jobs) as pool:
        for r in pool.imap_unordered(fpcalc_one, audio_files, chunksize=8):
            if on_progress is not None:
                on_progress(1)
            if r is not None:
                rows.append(r)
    return rows


def fp_row_sort_key(row: FingerprintRow) -> str:
    """Sort key for deterministic TSV output."""
    return row.path.as_posix()
