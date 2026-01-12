#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
discog_dedupe_audio.py

Find releases that fully duplicate the audio content of other releases.
Uses Chromaprint fingerprints via fpcalc; metadata and covers are ignored.

Rules:
- A release can be removed only if ALL its tracks (duration+fingerprint) exist
  inside ONE other release.
- Exact duplicates (same track set) keep the "best" release, remove the rest.
- If a release has unique tracks, it must not be removed (safety check).

Default: do not delete anything, only write reports.
Optional: --move-to DIR (move candidates) or --delete (remove).
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from .core.constants import AUDIO_EXTS_DEFAULT
from .dedupe_fingerprint import fingerprint_files, fp_row_sort_key
from .dedupe_logic import build_release_keys, find_redundant_releases
from .dedupe_reporting import apply_actions, ensure_dir, print_summary, write_reports
from .dedupe_scan import iter_audio_files


def which_or_die(cmd: str) -> None:
    if shutil.which(cmd) is None:
        print(f"ERROR: '{cmd}' not found in PATH. Install chromaprint (fpcalc).", file=sys.stderr)
        sys.exit(2)


def add_dedupe_subparser(subparsers) -> argparse.ArgumentParser:
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
        default=max(1, (os.cpu_count() or 2)),
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
    return parser


def run_dedupe(args: argparse.Namespace) -> int:
    which_or_die("fpcalc")

    if args.delete and args.move_to:
        print("ERROR: --delete and --move-to cannot be used together", file=sys.stderr)
        return 2

    roots = [Path(r) for r in args.roots]
    exts = {e.lower() if e.startswith(".") else "." + e.lower() for e in args.ext}
    out_dir = Path(args.out_dir)
    ensure_dir(out_dir)

    audio_files = list(iter_audio_files(roots, exts))
    if not audio_files:
        print("No audio files found in the specified roots.", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"Audio files found: {len(audio_files)}")
        print(f"Computing fpcalc fingerprints (jobs={args.jobs})...")

    rows = fingerprint_files(audio_files, args.jobs)
    if not rows:
        print("fpcalc failed to process any files (check codecs/files).", file=sys.stderr)
        return 1

    # Fingerprints TSV
    tsv_path = out_dir / "discog_audiofp.tsv"
    rows.sort(key=fp_row_sort_key)
    with tsv_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(f"{row.duration}\t{row.fingerprint}\t{row.path}\n")

    release_keys = build_release_keys(rows)
    result = find_redundant_releases(release_keys)
    paths = write_reports(result, out_dir)

    if not args.quiet:
        print_summary(result, paths, out_dir)

    apply_actions(result, move_to=args.move_to, delete=args.delete, quiet=args.quiet)

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Find duplicate releases by audio content (Chromaprint/fpcalc)."
    )
    add_dedupe_subparser(ap.add_subparsers(dest="command"))
    args = ap.parse_args()
    if args.command != "dedupe":
        ap.print_help()
        return 1
    return run_dedupe(args)


if __name__ == "__main__":
    raise SystemExit(main())
