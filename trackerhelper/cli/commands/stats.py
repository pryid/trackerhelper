from __future__ import annotations

import argparse
from pathlib import Path

from ..args import add_common_audio_args, normalize_exts
from ..common import ensure_executable, ensure_root
from ...app.stats import collect_stats, collect_synthetic_stats
from ...domain.grouping import group_releases
from ...domain.utils import bit_label, format_hhmmss, release_word, sr_label, track_word
from ...infra.ffprobe import FfprobeClient


def add_parser(subparsers) -> argparse.ArgumentParser:
    """Register the stats subcommand parser."""
    parser = subparsers.add_parser("stats", help="Print grouped stats.")
    add_common_audio_args(parser, include_root=True)
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Generate fake data (no ffprobe/files needed) to test output formatting.",
    )
    return parser


def _format_release_path(root: Path, release_path: Path) -> str:
    rel_path = release_path.relative_to(root)
    return Path(*rel_path.parts[1:]).as_posix() if len(rel_path.parts) > 1 else rel_path.as_posix()


def run(args: argparse.Namespace) -> int:
    """Execute the stats command."""
    root = Path(args.root).expanduser().resolve()

    if not args.synthetic and not ensure_root(root):
        return 2

    if not args.synthetic and not ensure_executable("ffprobe"):
        return 3

    exts = normalize_exts(args.ext)
    if args.synthetic:
        releases, summary = collect_synthetic_stats(root)
    else:
        ffprobe = FfprobeClient()
        releases, summary = collect_stats(root, exts, args.include_root, ffprobe)

    if not releases:
        print("No audio files found.")
        return 0

    groups = group_releases(releases, root)
    for i, group in enumerate(groups):
        if i:
            print()
        print(f"{group.name}:")
        for rel in group.releases:
            pretty = _format_release_path(root, rel.path)
            print(
                f"  {pretty} - {format_hhmmss(rel.duration_seconds)} "
                f"({rel.track_count} {track_word(rel.track_count)}, "
                f"{bit_label(rel.bit_depths)}, {sr_label(rel.sample_rates)})"
            )

    total_releases = len(releases)
    print(
        f"\nTotal: {format_hhmmss(summary.total_seconds)} "
        f"({summary.total_tracks} {track_word(summary.total_tracks)}, "
        f"{total_releases} {release_word(total_releases)})"
    )

    return 0
