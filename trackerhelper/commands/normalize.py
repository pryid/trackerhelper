from __future__ import annotations

import argparse
from pathlib import Path

from ..cli_args import add_common_audio_args, normalize_exts
from .common import ensure_ffprobe, ensure_root
from ..core.normalize import normalize_release_folders


def add_parser(subparsers) -> argparse.ArgumentParser:
    """Register the normalize subcommand parser."""
    parser = subparsers.add_parser("normalize", help="Normalize release folder names (dry run by default).")
    add_common_audio_args(parser)
    parser.add_argument("--apply", "--y", dest="apply", action="store_true", help="Apply rename changes.")
    return parser


def run(args: argparse.Namespace) -> int:
    """Execute the normalize command."""
    root = Path(args.path).expanduser().resolve()

    if not ensure_root(root):
        return 2

    if not ensure_ffprobe():
        return 3

    exts = normalize_exts(args.ext)
    normalize_release_folders(root, exts, apply=args.apply)
    return 0
