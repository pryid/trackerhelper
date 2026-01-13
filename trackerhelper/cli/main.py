from __future__ import annotations

import argparse
import logging
import sys

from .commands import dedupe as dedupe_cmd
from .commands import normalize as normalize_cmd
from .commands import release as release_cmd
from .commands import stats as stats_cmd
from ..logging_utils import setup_logging
from .. import __version__

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Sum durations grouped per release folder; show bit depth + sample rate; "
            "optionally generate BBCode release template."
        )
    )
    parser.add_argument("--version", action="version", version=f"trackerhelper {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    stats_cmd.add_parser(subparsers)
    release_cmd.add_parser(subparsers)
    normalize_cmd.add_parser(subparsers)
    dedupe_cmd.add_parser(subparsers)

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    setup_logging()
    logger.info("trackerhelper %s", __version__)
    parser = build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if args.command == "stats":
        return stats_cmd.run(args)
    if args.command == "release":
        return release_cmd.run(args)
    if args.command == "normalize":
        return normalize_cmd.run(args)
    if args.command == "dedupe":
        return dedupe_cmd.run(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
