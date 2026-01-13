from __future__ import annotations

import argparse
from pathlib import Path

from ..args import add_no_progress_arg, normalize_exts
from ...app.dedupe import default_jobs, run_dedupe
from ..progress import progress_bar
from ...domain.constants import AUDIO_EXTS_DEFAULT


def add_parser(subparsers) -> argparse.ArgumentParser:
    """Register the dedupe subcommand parser."""
    parser = subparsers.add_parser(
        "dedupe",
        help="Find duplicate releases by audio fingerprint.",
        description="Find duplicate releases by audio content (Chromaprint/fpcalc).",
    )
    parser.add_argument(
        "--roots",
        nargs="*",
        default=["Albums", "Singles"],
        help="Root folders to scan (default: Albums Singles).",
    )
    parser.add_argument(
        "--ext",
        nargs="*",
        default=sorted(AUDIO_EXTS_DEFAULT),
        help="Audio extensions list (default: common formats).",
    )
    parser.add_argument(
        "--out-dir",
        default="_dedupe_reports",
        help="Where to write reports (default: ./_dedupe_reports).",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=default_jobs(),
        help="Parallelism for fpcalc (default: cpu_count).",
    )
    parser.add_argument(
        "--move-to",
        default=None,
        help="If set: move duplicate releases to the folder (no deletion).",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="If set: delete duplicate releases (dangerous).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce stdout output.",
    )
    add_no_progress_arg(parser)
    return parser


def run(args: argparse.Namespace) -> int:
    """Execute the dedupe command."""
    roots = [Path(r).expanduser().resolve() for r in args.roots]
    exts = normalize_exts(args.ext, base_exts=set())
    out_dir = Path(args.out_dir).expanduser().resolve()
    move_to = Path(args.move_to).expanduser().resolve() if args.move_to else None

    if args.quiet:
        return run_dedupe(
            roots=roots,
            exts=exts,
            out_dir=out_dir,
            jobs=args.jobs,
            move_to=move_to,
            delete=args.delete,
            quiet=True,
        )
    if args.no_progress:
        return run_dedupe(
            roots=roots,
            exts=exts,
            out_dir=out_dir,
            jobs=args.jobs,
            move_to=move_to,
            delete=args.delete,
            quiet=False,
        )

    with progress_bar("Fingerprinting audio") as progress:
        return run_dedupe(
            roots=roots,
            exts=exts,
            out_dir=out_dir,
            jobs=args.jobs,
            move_to=move_to,
            delete=args.delete,
            quiet=False,
            progress=progress,
        )
