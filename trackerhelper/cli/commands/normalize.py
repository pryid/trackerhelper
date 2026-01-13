from __future__ import annotations

import argparse
from pathlib import Path

from ..args import add_common_audio_args, add_no_progress_arg, normalize_exts
from ..common import ensure_executable, ensure_root
from ...app.normalize import apply_normalization, plan_normalization
from ..progress import progress_bar


def add_parser(subparsers) -> argparse.ArgumentParser:
    """Register the normalize subcommand parser."""
    parser = subparsers.add_parser("normalize", help="Normalize release folder names (dry run by default).")
    add_common_audio_args(parser)
    add_no_progress_arg(parser)
    parser.add_argument("--apply", dest="apply", action="store_true", help="Apply rename changes.")
    return parser


def _display_path(root: Path, p: Path) -> str:
    if p == root or p.parent == root.parent:
        return p.name
    try:
        rel = p.relative_to(root)
    except ValueError:
        return p.as_posix()
    return p.name if str(rel) == "." else rel.as_posix()


def run(args: argparse.Namespace) -> int:
    """Execute the normalize command."""
    root = Path(args.root).expanduser().resolve()

    if not ensure_root(root):
        return 2

    if not ensure_executable("ffprobe"):
        return 3

    exts = normalize_exts(args.ext)
    if args.no_progress:
        plan = plan_normalization(root, exts)
    else:
        with progress_bar("Reading tags") as progress:
            plan = plan_normalization(root, exts, progress=progress)

    if not plan.actions and not plan.skipped:
        print("No audio files found for normalization.")
        return 0

    if plan.skipped:
        print("Skipped:")
        for item in plan.skipped:
            print(f"  {_display_path(root, item.path)} ({item.reason})")
        if not plan.actions:
            print("Nothing to normalize.")
            return 0

    if not args.apply:
        print("Planned changes (use --apply to apply):")
        for action in plan.actions:
            print(f"  {_display_path(root, action.source)} -> {_display_path(root, action.target)}")
        return len(plan.actions)

    count = apply_normalization(plan)
    for action in plan.actions:
        print(f"Renamed: {_display_path(root, action.source)} -> {_display_path(root, action.target)}")
    return count
