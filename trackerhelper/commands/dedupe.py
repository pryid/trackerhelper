from __future__ import annotations

import argparse

from ..dedupe import add_dedupe_subparser, run_dedupe


def add_parser(subparsers) -> argparse.ArgumentParser:
    """Register the dedupe subcommand parser."""
    return add_dedupe_subparser(subparsers)


def run(args: argparse.Namespace) -> int:
    """Execute the dedupe command."""
    return run_dedupe(args)
