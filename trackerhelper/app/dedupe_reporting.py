from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from ..domain.dedupe import DedupeResult


@dataclass(frozen=True)
class DedupeReportPaths:
    report_path: Path
    list_path: Path
    post_path: Path


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def safe_move(src: Path, dst_dir: Path) -> Path:
    """
    Move src into dst_dir. If the name exists, append a time suffix.
    """
    ensure_dir(dst_dir)
    target = dst_dir / src.name
    if target.exists():
        suffix = time.strftime("%Y%m%d-%H%M%S")
        target = dst_dir / f"{src.name}__{suffix}"
    shutil.move(str(src), str(target))
    return target


def write_reports(result: DedupeResult, out_dir: Path) -> DedupeReportPaths:
    """Write the main dedupe reports to disk."""
    report_path = out_dir / "discog_redundancy_report.txt"
    list_path = out_dir / "discog_redundant_dirs.txt"
    post_path = out_dir / "discog_postcheck_contained.txt"

    lines: list[str] = []
    lines.append("=== DISCOGRAPHY REDUNDANCY REPORT (audio-content) ===\n")
    lines.append("Rule: remove a release only if ALL its tracks exist in ONE other release.\n")
    lines.append("Exact duplicates keep the best release (Albums > Singles, Deluxe/Edition preferred).\n\n")

    if result.unsafe:
        lines.append("!!! SAFETY: these releases were candidates but have unique tracks and are NOT removed:\n")
        for r in result.unsafe:
            lines.append(
                f"UNSAFE: {r.as_posix()}  unique_tracks={result.unique_count[r]}  "
                f"total_tracks={result.sizes[r]}\n"
            )
        lines.append("\n")

    if not result.redundant:
        lines.append("Nothing to remove: no releases fully covered by others.\n")
    else:
        dups = sorted(
            [r for r in result.redundant if r in result.duplicate_of],
            key=lambda r: r.as_posix(),
        )
        subs = sorted(
            [r for r in result.redundant if r not in result.duplicate_of],
            key=lambda r: r.as_posix(),
        )

        if dups:
            lines.append("== EXACT DUPLICATES (same track set) ==\n")
            for r in dups:
                lines.append(
                    f"DELETE: {r.as_posix()}\n"
                    f"  identical_to: {result.duplicate_of[r].as_posix()}\n"
                    f"  tracks: {result.sizes[r]}\n\n"
                )

        if subs:
            lines.append("== FULLY CONTAINED (release is a subset of another release) ==\n")
            for r in subs:
                c = result.contained_in.get(r)
                contained = c.as_posix() if isinstance(c, Path) else "?"
                size_val = result.sizes.get(c) if isinstance(c, Path) else None
                size_label = str(size_val) if size_val is not None else "?"
                lines.append(
                    f"DELETE: {r.as_posix()}\n"
                    f"  contained_in: {contained}\n"
                    f"  tracks: {result.sizes[r]} -> {size_label}\n"
                    f"  unique_tracks_in_release: {result.unique_count[r]}\n\n"
                )

    report_path.write_text("".join(lines), encoding="utf-8")

    with list_path.open("w", encoding="utf-8") as f:
        for r in sorted(result.redundant, key=lambda r: r.as_posix()):
            f.write(r.as_posix() + "\n")

    with post_path.open("w", encoding="utf-8") as f:
        for rel in result.post_contained:
            f.write(f"{rel.subset.as_posix()}\t<=\t{rel.superset.as_posix()}\n")

    return DedupeReportPaths(report_path=report_path, list_path=list_path, post_path=post_path)


def print_summary(result: DedupeResult, paths: DedupeReportPaths, out_dir: Path) -> None:
    """Print a short summary of dedupe results."""
    print(f"Done. Reports in: {out_dir}")
    print(f"  - {paths.report_path}")
    print(f"  - {paths.list_path}")
    print(f"  - {paths.post_path}")
    print(f"Candidates to remove/move: {len(result.redundant)}")
    if result.post_contained:
        print(f"Post-check: subset relationships remain: {len(result.post_contained)} (see {paths.post_path})")
    else:
        print("Post-check: OK (no remaining A subset of B relationships).")


def apply_actions(result: DedupeResult, *, move_to: str | None, delete: bool, quiet: bool) -> None:
    """Move/delete redundant releases based on flags."""
    if move_to:
        dst = Path(move_to)
        ensure_dir(dst)
        moved = 0
        for r in sorted(result.redundant, key=lambda r: r.as_posix()):
            src = r
            if src.exists():
                safe_move(src, dst)
                moved += 1
        if not quiet:
            print(f"Moved releases: {moved} -> {dst}")

    if delete:
        deleted = 0
        for r in sorted(result.redundant, key=lambda r: r.as_posix()):
            src = r
            if src.exists():
                shutil.rmtree(src)
                deleted += 1
        if not quiet:
            print(f"Deleted releases: {deleted}")
