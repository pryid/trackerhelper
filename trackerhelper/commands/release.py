from __future__ import annotations

import argparse
import logging
from pathlib import Path

from ..cli_args import add_common_audio_args, normalize_exts
from .common import ensure_ffprobe, ensure_root
from ..core.grouping import ReleaseBBCodeItem, group_bbcode_releases
from ..core.models import ReleaseBBCode
from ..core.stats import collect_real_stats, collect_synthetic_stats
from ..core.utils import bit_label, codec_label, format_hhmmss, group_key, parse_release_title_and_year, sr_label
from ..formatting.bbcode import make_release_bbcode, make_single_release_bbcode
from ..formatting.tracklist import build_tracklist_lines
from ..io.cover import FastPicCoverUploader, find_cover_jpg, requests as cover_requests
from ..io.dr_utils import build_dr_index, find_dr_text_for_release
from ..io.ffprobe_utils import FfprobeClient

logger = logging.getLogger(__name__)


def add_parser(subparsers) -> argparse.ArgumentParser:
    """Register the release subcommand parser."""
    parser = subparsers.add_parser("release", help="Generate BBCode release template.")
    add_common_audio_args(parser, include_root=True)
    parser.add_argument("--dr", default=None, help="Directory with DR reports (e.g. *_dr.txt).")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Generate fake data (no ffprobe/files needed) to test output formatting.",
    )
    parser.add_argument("--no-cover", action="store_true", help="Disable cover upload to FastPic.")
    parser.add_argument("--bbcode-lang", choices=["ru", "en"], default="ru", help="BBCode language (default: ru).")
    parser.add_argument("--bbcode-en", action="store_true", help="Shortcut for --bbcode-lang en.")
    return parser


def _resolve_bbcode_lang(args: argparse.Namespace) -> str:
    """Return the effective BBCode language."""
    lang = args.bbcode_lang
    if args.bbcode_en:
        lang = "en"
    return lang


def run(args: argparse.Namespace) -> int:
    """Execute the release command."""
    root = Path(args.path).expanduser().resolve()

    if not args.test and not ensure_root(root):
        return 2

    if not args.test and not ensure_ffprobe():
        return 3

    exts = normalize_exts(args.ext)
    if args.test:
        releases, summary = collect_synthetic_stats(root)
    else:
        ffprobe = FfprobeClient()
        releases, summary = collect_real_stats(root, exts, args.include_root, ffprobe)

    if not releases:
        print("No audio files found.")
        return 0

    dr_dir: Path | None = None
    dr_index: dict[str, Path] = {}
    if args.dr is not None:
        dr_dir = Path(args.dr).expanduser().resolve()
        if not dr_dir.exists() or not dr_dir.is_dir():
            logger.warning("Warning: --dr path is not a directory: %s", dr_dir)
            dr_dir = None
        else:
            dr_index = build_dr_index(dr_dir)

    cover_uploader: FastPicCoverUploader | None = None
    if not args.test and not args.no_cover:
        if cover_requests is None:
            logger.warning("Warning: 'requests' not installed; skipping FastPic cover uploads.")
        else:
            cover_uploader = FastPicCoverUploader(resize_to=500)

    year_range = None
    if summary.all_years:
        y_min, y_max = min(summary.all_years), max(summary.all_years)
        year_range = f"{y_min}-{y_max}" if y_min != y_max else f"{y_min}"

    items: list[ReleaseBBCodeItem] = []
    for rel in releases:
        rel_path = rel.path.relative_to(root)
        group = group_key(rel_path)

        folder_name = rel.path.name
        title, year = parse_release_title_and_year(folder_name)
        tracklist = build_tracklist_lines(rel.audio_files, sort=False)

        dr_text = None
        if args.test:
            dr_text = rel.dr_text
        elif dr_dir is not None:
            dr_text = find_dr_text_for_release(folder_name, dr_dir, dr_index)

        cover_url = None
        if cover_uploader is not None:
            cover_path = find_cover_jpg(rel.path)
            if cover_path is not None:
                try:
                    cover_url = cover_uploader.upload(cover_path)
                except Exception as e:
                    logger.warning("Warning: cover upload failed for %s: %s", cover_path, e)

        items.append(
            ReleaseBBCodeItem(
                group=group,
                release=ReleaseBBCode(
                    title=title,
                    year=year,
                    duration=format_hhmmss(rel.duration_seconds),
                    tracklist=tracklist,
                    dr=dr_text,
                    cover_url=cover_url,
                ),
            )
        )

    total_releases = len(releases)
    lang = _resolve_bbcode_lang(args)
    groups = group_bbcode_releases(items)

    if total_releases == 1:
        single_release = groups[0].releases[0] if groups and groups[0].releases else None
        if single_release is None:
            logger.warning("Warning: no releases found for BBCode generation.")
            return 0

        bbcode = make_single_release_bbcode(
            root_name=root.name,
            year_range=year_range,
            overall_codec=codec_label(summary.total_exts),
            release=single_release,
            lang=lang,
        )
    else:
        bbcode = make_release_bbcode(
            root_name=root.name,
            year_range=year_range,
            total_duration=format_hhmmss(summary.total_seconds),
            overall_codec=codec_label(summary.total_exts),
            overall_bit=bit_label(summary.total_bit),
            overall_sr=sr_label(summary.total_sr),
            grouped_releases=groups,
            lang=lang,
        )

    out_path = Path.cwd() / f"{root.name}.txt"
    out_path.write_text(bbcode, encoding="utf-8")
    print(f"\nWrote release template: {out_path}")
    return 0
