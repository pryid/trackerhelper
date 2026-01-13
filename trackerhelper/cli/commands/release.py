from __future__ import annotations

import argparse
import logging
from pathlib import Path

from ..args import add_common_audio_args, add_no_progress_arg, normalize_exts
from ..common import ensure_outside_roots, prepare_audio_root
from ..progress import run_with_progress
from ...app.release import build_release_bbcode
from ...formatting.release import render_missing_assets_report

logger = logging.getLogger(__name__)


def add_parser(subparsers) -> argparse.ArgumentParser:
    """Register the release subcommand parser."""
    parser = subparsers.add_parser("release", help="Generate BBCode release template.")
    add_common_audio_args(parser, include_root=True)
    add_no_progress_arg(parser)
    parser.add_argument("--dr-dir", default=None, help="Directory with DR reports (e.g. *_dr.txt).")
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Generate fake data (no ffprobe/files needed) to test output formatting.",
    )
    parser.add_argument("--no-cover", action="store_true", help="Disable cover upload to FastPic.")
    parser.add_argument("--lang", choices=["ru", "en"], default="ru", help="BBCode language (default: ru).")
    parser.add_argument(
        "--output",
        default=None,
        help="Write BBCode output to a file (default: ./<root>.txt).",
    )
    parser.add_argument(
        "--report-missing",
        nargs="?",
        const="missing_report.txt",
        default=None,
        help="Write a report of releases missing cover.jpg or DR reports.",
    )
    return parser


def run(args: argparse.Namespace) -> int:
    """Execute the release command."""
    root, err = prepare_audio_root(args.root, skip_checks=args.synthetic)
    if err is not None:
        return err

    exts = normalize_exts(args.ext)

    dr_dir: Path | None = None
    if args.dr_dir is not None:
        dr_dir = Path(args.dr_dir).expanduser().resolve()
        if not dr_dir.exists() or not dr_dir.is_dir():
            logger.warning("Warning: --dr-dir path is not a directory: %s", dr_dir)
            dr_dir = None

    if args.synthetic:
        result = build_release_bbcode(
            root,
            exts,
            args.include_root,
            dr_dir=dr_dir,
            test_mode=True,
            no_cover=args.no_cover,
            lang=args.lang,
        )
    else:
        result = run_with_progress(
            args.no_progress,
            False,
            "Reading audio metadata",
            lambda progress: build_release_bbcode(
                root,
                exts,
                args.include_root,
                dr_dir=dr_dir,
                test_mode=False,
                no_cover=args.no_cover,
                lang=args.lang,
                progress=progress,
            ),
        )

    if result is None:
        print("No audio files found.")
        return 0

    if args.output is not None:
        out_path = Path(args.output).expanduser().resolve()
    else:
        out_path = Path.cwd() / f"{root.name}.txt"
    if not ensure_outside_roots(out_path, [root], "output file"):
        return 2
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(result.bbcode, encoding="utf-8")
    print(f"\nWrote release template: {out_path}")

    if args.report_missing is not None:
        report_path = Path(args.report_missing).expanduser().resolve()
        if not ensure_outside_roots(report_path, [root], "missing report file"):
            return 2
        report_text = render_missing_assets_report(result, root, dr_dir=dr_dir)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_text, encoding="utf-8")
        print(f"Wrote missing report: {report_path}")
    return 0
