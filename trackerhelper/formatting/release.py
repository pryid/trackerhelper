from __future__ import annotations

from pathlib import Path

from ..app.release import ReleaseBuildResult


def _format_rel_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def render_missing_assets_report(
    result: ReleaseBuildResult,
    root: Path,
    *,
    dr_dir: Path | None,
) -> str:
    lines: list[str] = []
    lines.append(f"Missing assets report for: {root.name}")
    lines.append(f"Root: {root}")
    if dr_dir is None:
        lines.append("DR check: disabled (--dr-dir not set)")
    else:
        lines.append(f"DR directory: {dr_dir}")

    lines.append("")
    if result.missing_covers:
        lines.append(f"Missing cover.jpg: {len(result.missing_covers)}")
        for rel in sorted(result.missing_covers, key=lambda p: p.as_posix()):
            lines.append(f"- {_format_rel_path(root, rel)}")
    else:
        lines.append("Missing cover.jpg: 0")

    lines.append("")
    if not result.dr_checked:
        lines.append("Missing DR reports: skipped")
    elif result.missing_drs:
        lines.append(f"Missing DR reports: {len(result.missing_drs)}")
        for rel in sorted(result.missing_drs, key=lambda p: p.as_posix()):
            lines.append(f"- {_format_rel_path(root, rel)}")
    else:
        lines.append("Missing DR reports: 0")

    return "\n".join(lines)
