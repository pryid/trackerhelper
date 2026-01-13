from __future__ import annotations

from pathlib import Path

from ..infra.scan import ReleaseScan, iter_release_scans


def list_release_scans(
    root: Path,
    exts: set[str],
    include_root: bool,
    *,
    sort: bool = True,
) -> list[ReleaseScan]:
    """Return release scans with optional sorting."""
    scans = list(iter_release_scans(root, exts, include_root))
    if sort:
        scans.sort(key=lambda item: item.path.as_posix().lower())
    return scans
