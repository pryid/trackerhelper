from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .bbcode import make_release_bbcode, make_single_release_bbcode
from .constants import AUDIO_EXTS_DEFAULT
from .cover import FastPicCoverUploader, find_cover_jpg, requests as cover_requests
from .dr_utils import build_dr_index, find_dr_text_for_release
from .ffprobe_utils import FfprobeClient
from .dedupe import add_dedupe_subparser, run_dedupe
from .models import ReleaseBBCode
from .normalize import normalize_release_folders
from .stats import collect_real_stats, collect_synthetic_stats
from .tracklist import build_tracklist_lines
from .utils import (
    bit_label,
    codec_label,
    format_hhmmss,
    group_key,
    group_sort_index,
    parse_release_title_and_year,
    release_word,
    sr_label,
    track_word,
    which,
)


def normalize_exts(user_exts: list[str]) -> set[str]:
    """Merge default extensions with user-provided --ext values."""
    exts = set(AUDIO_EXTS_DEFAULT)
    for e in user_exts:
        e = e.strip().lower()
        if e and not e.startswith("."):
            e = "." + e
        if e:
            exts.add(e)
    return exts


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Sum durations grouped per release folder; show bit depth + sample rate; optionally generate BBCode release template."
    )
    subparsers = ap.add_subparsers(dest="command")

    stats_p = subparsers.add_parser("stats", help="Print grouped stats.")
    stats_p.add_argument("path", nargs="?", default=".", help="Root folder (default: current directory).")
    stats_p.add_argument("--ext", action="append", default=[], help="Add extension (e.g. --ext .flac). Repeatable.")
    stats_p.add_argument("--include-root", action="store_true", help="Include tracks directly inside the root folder.")
    stats_p.add_argument("--test", action="store_true", help="Generate fake data (no ffprobe/files needed) to test output formatting.")

    release_p = subparsers.add_parser("release", help="Generate BBCode release template.")
    release_p.add_argument("path", nargs="?", default=".", help="Root folder (default: current directory).")
    release_p.add_argument("--ext", action="append", default=[], help="Add extension (e.g. --ext .flac). Repeatable.")
    release_p.add_argument("--include-root", action="store_true", help="Include tracks directly inside the root folder.")
    release_p.add_argument("--dr", default=None, help="Directory with DR reports (e.g. *_dr.txt).")
    release_p.add_argument("--test", action="store_true", help="Generate fake data (no ffprobe/files needed) to test output formatting.")
    release_p.add_argument("--no-cover", action="store_true", help="Disable cover upload to FastPic.")
    release_p.add_argument("--bbcode-lang", choices=["ru", "en"], default="ru", help="BBCode language (default: ru).")
    release_p.add_argument("--bbcode-en", action="store_true", help="Shortcut for --bbcode-lang en.")

    normalize_p = subparsers.add_parser("normalize", help="Normalize release folder names (dry run by default).")
    normalize_p.add_argument("path", nargs="?", default=".", help="Root folder (default: current directory).")
    normalize_p.add_argument("--ext", action="append", default=[], help="Add extension (e.g. --ext .flac). Repeatable.")
    normalize_p.add_argument("--apply", "--y", dest="apply", action="store_true", help="Apply rename changes.")

    add_dedupe_subparser(subparsers)

    return ap


def ensure_root(root: Path) -> bool:
    if not root.exists() or not root.is_dir():
        print(f"Error: '{root}' is not a directory.", file=sys.stderr)
        return False
    return True


def ensure_ffprobe() -> bool:
    if which("ffprobe") is None:
        print("Error: ffprobe not found. Install ffmpeg (ffprobe) and retry.", file=sys.stderr)
        return False
    return True


def run_stats(args: argparse.Namespace) -> int:
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

    items = []
    for rel in releases:
        rel_path = rel.path.relative_to(root)
        items.append((rel_path, rel))

    items.sort(key=lambda x: (group_sort_index(group_key(x[0])), x[0].as_posix().lower()))

    current_group = None
    for rel_path, rel in items:
        g = group_key(rel_path)
        if g != current_group:
            if current_group is not None:
                print()
            print(f"{g}:")
            current_group = g

        pretty = Path(*rel_path.parts[1:]).as_posix() if len(rel_path.parts) > 1 else rel_path.as_posix()
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


def run_release(args: argparse.Namespace) -> int:
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
            print(f"Warning: --dr path is not a directory: {dr_dir}", file=sys.stderr)
            dr_dir = None
        else:
            dr_index = build_dr_index(dr_dir)

    cover_uploader: FastPicCoverUploader | None = None
    if not args.test and not args.no_cover:
        if cover_requests is None:
            print("Warning: 'requests' not installed; skipping FastPic cover uploads.", file=sys.stderr)
        else:
            cover_uploader = FastPicCoverUploader(resize_to=500)

    year_range = None
    if summary.all_years:
        y_min, y_max = min(summary.all_years), max(summary.all_years)
        year_range = f"{y_min}-{y_max}" if y_min != y_max else f"{y_min}"

    grouped: dict[str, list[ReleaseBBCode]] = {}
    for rel in releases:
        rel_path = rel.path.relative_to(root)
        g = group_key(rel_path)

        folder_name = rel.path.name
        title, year = parse_release_title_and_year(folder_name)

        tracklist = build_tracklist_lines(rel.audio_files)

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
                    print(f"Warning: cover upload failed for {cover_path}: {e}", file=sys.stderr)

        grouped.setdefault(g, []).append(
            ReleaseBBCode(
                title=title,
                year=year,
                duration=format_hhmmss(rel.duration_seconds),
                tracklist=tracklist,
                dr=dr_text,
                cover_url=cover_url,
            )
        )

    for g, lst in grouped.items():
        lst.sort(key=lambda r: ((r.year or 9999), str(r.title).lower()))

    total_releases = len(releases)
    lang = args.bbcode_lang
    if args.bbcode_en:
        lang = "en"

    if total_releases == 1:
        single_release = None
        for rels in grouped.values():
            if rels:
                single_release = rels[0]
                break

        if single_release is None:
            print("Warning: no releases found for BBCode generation.", file=sys.stderr)
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
            grouped_releases=grouped,
            lang=lang,
        )

    out_path = Path.cwd() / f"{root.name}.txt"
    out_path.write_text(bbcode, encoding="utf-8")
    print(f"\nWrote release template: {out_path}")

    return 0


def run_normalize(args: argparse.Namespace) -> int:
    root = Path(args.path).expanduser().resolve()

    if not ensure_root(root):
        return 2

    if not ensure_ffprobe():
        return 3

    exts = normalize_exts(args.ext)
    normalize_release_folders(root, exts, apply=args.apply)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if args.command == "stats":
        return run_stats(args)
    if args.command == "release":
        return run_release(args)
    if args.command == "normalize":
        return run_normalize(args)
    if args.command == "dedupe":
        return run_dedupe(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
