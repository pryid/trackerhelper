from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..args import add_no_progress_arg, normalize_exts
from ..progress import run_with_progress
from ...app.dedupe import apply_plan, default_jobs, run_dedupe
from ...domain.constants import AUDIO_EXTS_DEFAULT
from ...formatting.dedupe import dedupe_result_to_dict, render_dedupe_csv


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
        "--plan-out",
        default=None,
        help="Write a dedupe plan JSON (no deletion unless --move-to/--delete is set).",
    )
    parser.add_argument(
        "--apply-plan",
        default=None,
        help="Apply a previously generated plan JSON (skips scanning).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON report to stdout.",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Output CSV report to stdout.",
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
    if args.json and args.csv:
        print("Error: --json and --csv cannot be used together.")
        return 2

    if args.apply_plan and args.plan_out:
        print("Error: --apply-plan cannot be combined with --plan-out.")
        return 2

    if args.apply_plan:
        move_to = Path(args.move_to).expanduser().resolve() if args.move_to else None
        code, moved, deleted = apply_plan(
            Path(args.apply_plan).expanduser().resolve(),
            move_to=move_to,
            delete=args.delete,
            quiet=args.quiet or args.json or args.csv,
        )
        if code != 0:
            return code
        if args.json:
            print(json.dumps({"moved": moved, "deleted": deleted}, ensure_ascii=False))
        elif args.csv:
            print("moved,deleted")
            print(f"{moved},{deleted}")
        return 0

    roots = [Path(r).expanduser().resolve() for r in args.roots]
    exts = normalize_exts(args.ext, base_exts=set())
    out_dir = Path(args.out_dir).expanduser().resolve()
    move_to = Path(args.move_to).expanduser().resolve() if args.move_to else None
    plan_out = Path(args.plan_out).expanduser().resolve() if args.plan_out else None

    quiet = args.quiet or args.json or args.csv
    code, result, _ = run_with_progress(
        args.no_progress,
        quiet,
        "Fingerprinting audio",
        lambda progress: run_dedupe(
            roots=roots,
            exts=exts,
            out_dir=out_dir,
            jobs=args.jobs,
            move_to=move_to,
            delete=args.delete,
            quiet=quiet,
            progress=progress,
            plan_out=plan_out,
        ),
    )

    if code != 0:
        return code
    if result is None:
        return 1

    if args.json:
        print(json.dumps(dedupe_result_to_dict(result, roots=roots, exts=exts), ensure_ascii=False))
    elif args.csv:
        print(render_dedupe_csv(result))

    return 0
