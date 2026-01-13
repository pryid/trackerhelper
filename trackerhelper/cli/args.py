from __future__ import annotations

import argparse

from ..domain.constants import AUDIO_EXTS_DEFAULT


def normalize_exts(user_exts: list[str], base_exts: set[str] | None = None) -> set[str]:
    """Merge default extensions with user-provided --ext values."""
    exts = set(base_exts or AUDIO_EXTS_DEFAULT)
    for e in user_exts:
        e = e.strip().lower()
        if e and not e.startswith("."):
            e = "." + e
        if e:
            exts.add(e)
    return exts


def add_path_arg(parser: argparse.ArgumentParser) -> None:
    """Add a shared positional root argument."""
    parser.add_argument("root", nargs="?", default=".", help="Root folder (default: current directory).")


def add_ext_arg(parser: argparse.ArgumentParser) -> None:
    """Add a shared --ext argument for audio extensions."""
    parser.add_argument("--ext", action="append", default=[], help="Add extension (e.g. --ext .flac). Repeatable.")


def add_include_root_arg(parser: argparse.ArgumentParser) -> None:
    """Add the --include-root flag for root-level tracks."""
    parser.add_argument("--include-root", action="store_true", help="Include tracks directly inside the root folder.")


def add_common_audio_args(parser: argparse.ArgumentParser, *, include_root: bool = False) -> None:
    """Add common path/extension args to a parser."""
    add_path_arg(parser)
    add_ext_arg(parser)
    if include_root:
        add_include_root_arg(parser)
