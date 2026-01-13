from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..args import add_no_progress_arg, normalize_exts
from ..common import ensure_outside_roots
from ..progress import run_with_progress
from ...app.dedupe import apply_plan, default_jobs, load_plan, run_dedupe
from ...domain.constants import AUDIO_EXTS_DEFAULT
from ...formatting.dedupe import dedupe_result_to_dict, iter_dedupe_jsonl, render_dedupe_csv


def _protected_roots(roots: list[Path]) -> list[Path]:
    protected = list(roots)
    if len(roots) > 1:
        parents = {root.parent for root in roots}
        if len(parents) == 1:
            parent = parents.pop()
            if parent not in protected:
                protected.append(parent)
    return protected


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
        "--jsonl",
        action="store_true",
        help="Output JSON Lines report to stdout.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Write JSON/CSV/JSONL output to a file instead of stdout.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not delete or move releases; only report.",
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
    format_flags = [args.json, args.csv, args.jsonl]
    if sum(1 for flag in format_flags if flag) > 1:
        print("Error: --json, --csv, and --jsonl cannot be used together.")
        return 2
    if args.output and not any(format_flags):
        print("Error: --output requires --json, --csv, or --jsonl.")
        return 2
    if args.jsonl and args.apply_plan:
        print("Error: --jsonl cannot be used with --apply-plan.")
        return 2
    if args.dry_run and args.apply_plan:
        print("Error: --dry-run cannot be used with --apply-plan.")
        return 2

    if args.apply_plan and args.plan_out:
        print("Error: --apply-plan cannot be combined with --plan-out.")
        return 2

    if args.apply_plan:
        plan_path = Path(args.apply_plan).expanduser().resolve()
        plan_data = load_plan(plan_path)
        plan_roots = [Path(p).expanduser().resolve() for p in plan_data.get("roots", [])]
        protected_plan_roots = _protected_roots(plan_roots)
        move_to = Path(args.move_to).expanduser().resolve() if args.move_to else None
        if move_to is not None and protected_plan_roots:
            if not ensure_outside_roots(move_to, protected_plan_roots, "move target"):
                return 2
        out_path = Path(args.output).expanduser().resolve() if args.output else None
        if out_path is not None and protected_plan_roots:
            if not ensure_outside_roots(out_path, protected_plan_roots, "output file"):
                return 2
        quiet = args.quiet or args.json or args.csv or out_path is not None
        code, moved, deleted = apply_plan(
            plan_path,
            move_to=move_to,
            delete=args.delete,
            quiet=quiet,
        )
        if code != 0:
            return code
        if args.json:
            output = json.dumps({"moved": moved, "deleted": deleted}, ensure_ascii=False)
        elif args.csv:
            output = f"moved,deleted\n{moved},{deleted}"
        else:
            return 0
        if out_path is not None:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(output, encoding="utf-8")
        else:
            print(output)
        return 0

    roots = [Path(r).expanduser().resolve() for r in args.roots]
    protected_roots = _protected_roots(roots)
    exts = normalize_exts(args.ext, base_exts=set())
    out_dir = Path(args.out_dir).expanduser().resolve()
    move_to = Path(args.move_to).expanduser().resolve() if args.move_to else None
    plan_out = Path(args.plan_out).expanduser().resolve() if args.plan_out else None
    out_path = Path(args.output).expanduser().resolve() if args.output else None
    delete = args.delete

    if args.dry_run:
        move_to = None
        delete = False

    if not ensure_outside_roots(out_dir, protected_roots, "out dir"):
        return 2
    if plan_out is not None and not ensure_outside_roots(plan_out, protected_roots, "plan file"):
        return 2
    if out_path is not None and not ensure_outside_roots(out_path, protected_roots, "output file"):
        return 2
    if move_to is not None and not ensure_outside_roots(move_to, protected_roots, "move target"):
        return 2

    quiet = args.quiet or args.json or args.csv or args.jsonl or out_path is not None
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
            delete=delete,
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
        output = json.dumps(dedupe_result_to_dict(result, roots=roots, exts=exts), ensure_ascii=False)
        if out_path is not None:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(output, encoding="utf-8")
        else:
            print(output)
    elif args.csv:
        output = render_dedupe_csv(result)
        if out_path is not None:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(output, encoding="utf-8")
        else:
            print(output)
    elif args.jsonl:
        if out_path is not None:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("w", encoding="utf-8") as handle:
                for line in iter_dedupe_jsonl(result):
                    handle.write(line + "\n")
        else:
            for line in iter_dedupe_jsonl(result):
                print(line)

    return 0
