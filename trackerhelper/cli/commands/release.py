from __future__ import annotations

import argparse
import logging
from pathlib import Path

from ..args import add_common_audio_args, add_no_progress_arg, normalize_exts
from ..common import ensure_executable, ensure_root
from ...app.release import build_release_bbcode
from ..progress import progress_bar

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
    return parser


def run(args: argparse.Namespace) -> int:
    """Execute the release command."""
    root = Path(args.root).expanduser().resolve()

    if not args.synthetic and not ensure_root(root):
        return 2

    if not args.synthetic and not ensure_executable("ffprobe"):
        return 3

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
        if args.no_progress:
            result = build_release_bbcode(
                root,
                exts,
                args.include_root,
                dr_dir=dr_dir,
                test_mode=False,
                no_cover=args.no_cover,
                lang=args.lang,
            )
        else:
            with progress_bar("Reading audio metadata") as progress:
                result = build_release_bbcode(
                    root,
                    exts,
                    args.include_root,
                    dr_dir=dr_dir,
                    test_mode=False,
                    no_cover=args.no_cover,
                    lang=args.lang,
                    progress=progress,
                )

    if result is None:
        print("No audio files found.")
        return 0

    out_path = Path.cwd() / f"{root.name}.txt"
    out_path.write_text(result.bbcode, encoding="utf-8")
    print(f"\nWrote release template: {out_path}")
    return 0
