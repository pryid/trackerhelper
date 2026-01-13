from __future__ import annotations

import argparse
from pathlib import Path

from ..args import add_common_audio_args, add_no_progress_arg, normalize_exts
from ..common import ensure_outside_roots, prepare_audio_root
from ..progress import run_with_progress
from ...app.stats import collect_stats, collect_synthetic_stats
from ...domain.grouping import group_releases
from ...formatting.stats import (
    render_stats_csv,
    render_stats_csv_tracks,
    render_stats_json,
    render_stats_text,
)
from ...infra.ffprobe import FfprobeClient


def add_parser(subparsers) -> argparse.ArgumentParser:
    """Register the stats subcommand parser."""
    parser = subparsers.add_parser("stats", help="Print grouped stats.")
    add_common_audio_args(parser, include_root=True)
    add_no_progress_arg(parser)
    parser.add_argument("--json", action="store_true", help="Output JSON stats.")
    parser.add_argument("--csv", action="store_true", help="Output CSV stats.")
    parser.add_argument(
        "--per-track",
        action="store_true",
        help="Include per-track details in the output.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Write output to a file instead of stdout.",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Generate fake data (no ffprobe/files needed) to test output formatting.",
    )
    return parser


def run(args: argparse.Namespace) -> int:
    """Execute the stats command."""
    if args.json and args.csv:
        print("Error: --json and --csv cannot be used together.")
        return 2

    root, err = prepare_audio_root(args.root, skip_checks=args.synthetic)
    if err is not None:
        return err
    out_path: Path | None = None
    if args.output is not None:
        out_path = Path(args.output).expanduser().resolve()
        if not ensure_outside_roots(out_path, [root], "output file"):
            return 2

    exts = normalize_exts(args.ext)
    if args.synthetic:
        releases, summary = collect_synthetic_stats(root)
    else:
        ffprobe = FfprobeClient()
        releases, summary = run_with_progress(
            args.no_progress,
            args.json or args.csv,
            "Reading audio metadata",
            lambda progress: collect_stats(
                root,
                exts,
                args.include_root,
                ffprobe,
                progress=progress,
                include_tracks=args.per_track,
            ),
        )

    if not releases:
        if args.json:
            output = render_stats_json([], summary, root, include_tracks=args.per_track)
        elif args.csv:
            if args.per_track:
                output = render_stats_csv_tracks([], root)
            else:
                output = render_stats_csv([], root)
        else:
            output = "No audio files found."
        if out_path is not None:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(output, encoding="utf-8")
            return 0
        print(output)
        return 0

    groups = group_releases(releases, root)
    if args.json:
        output = render_stats_json(groups, summary, root, include_tracks=args.per_track)
        if out_path is not None:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(output, encoding="utf-8")
            return 0
        print(output)
        return 0
    if args.csv:
        if args.per_track:
            output = render_stats_csv_tracks(releases, root)
        else:
            output = render_stats_csv(releases, root)
        if out_path is not None:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(output, encoding="utf-8")
            return 0
        print(output)
        return 0

    output = render_stats_text(groups, summary, root, include_tracks=args.per_track)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        return 0
    print(output)
    return 0
