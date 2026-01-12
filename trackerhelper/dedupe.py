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
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple, List, Dict, Set


AUDIO_EXTS_DEFAULT = {
    ".flac", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".aiff", ".aif", ".wma"
}


@dataclass(frozen=True)
class TrackKey:
    duration: str
    fingerprint: str


def which_or_die(cmd: str) -> None:
    if shutil.which(cmd) is None:
        print(f"ERROR: '{cmd}' not found in PATH. Install chromaprint (fpcalc).", file=sys.stderr)
        sys.exit(2)


def is_audio_file(p: Path, exts: Set[str]) -> bool:
    return p.is_file() and p.suffix.lower() in exts


def iter_audio_files(roots: List[Path], exts: Set[str]) -> Iterable[Path]:
    for root in roots:
        if not root.exists():
            continue
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                p = Path(dirpath) / fn
                if is_audio_file(p, exts):
                    yield p


def fpcalc_one(path: Path) -> Optional[Tuple[str, str, str]]:
    """
    Return (duration, fingerprint, filepath) or None if fpcalc fails.
    """
    try:
        # fpcalc outputs lines like:
        # DURATION=xxx
        # FINGERPRINT=....
        res = subprocess.run(
            ["fpcalc", "--", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return None

    if res.returncode != 0 or not res.stdout:
        return None

    dur = ""
    fp = ""
    for line in res.stdout.splitlines():
        if line.startswith("DURATION="):
            dur = line.split("=", 1)[1].strip()
        elif line.startswith("FINGERPRINT="):
            fp = line.split("=", 1)[1].strip()

    if not dur or not fp:
        return None

    return dur, fp, str(path)


def release_dir_from_path(p: Path) -> Optional[str]:
    """
    Treat the first folder under Albums/ or Singles/ as the release.
    Example: Albums/Clams Casino - Moon Trip Radio - 2019/01 - ... ->
    Albums/Clams Casino - Moon Trip Radio - 2019
    """
    parts = list(p.parts)
    lower_parts = [part.lower() for part in parts]
    if "albums" in lower_parts:
        i = lower_parts.index("albums")
    elif "singles" in lower_parts:
        i = lower_parts.index("singles")
    else:
        return None
    if i + 1 >= len(parts):
        return None
    return str(Path(*parts[: i + 2]))


def score_release(rel: str) -> int:
    """
    Heuristic for "keep the best" when content is identical.
    """
    rel_path = Path(rel)
    parts = [part.lower() for part in rel_path.parts]
    s = rel.lower()
    sc = 0
    if "albums" in parts:
        sc += 100
    if "deluxe" in s:
        sc += 6
    if "edition" in s:
        sc += 4
    if "reimagined" in s:
        sc += 2
    if "sampler" in s:
        sc -= 3
    return sc


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def safe_move(src: Path, dst_dir: Path) -> Path:
    """
    Move src into dst_dir. If the name exists, append a time suffix.
    """
    ensure_dir(dst_dir)
    target = dst_dir / src.name
    if target.exists():
        suffix = time.strftime("%Y%m%d-%H%M%S")
        target = dst_dir / f"{src.name}__{suffix}"
    shutil.move(str(src), str(target))
    return target


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

    # Parallel fpcalc via multiprocessing (no external dependencies)
    from multiprocessing import Pool

    rows: List[Tuple[str, str, str]] = []
    with Pool(processes=args.jobs) as pool:
        for r in pool.imap_unordered(fpcalc_one, audio_files, chunksize=8):
            if r is not None:
                rows.append(r)

    if not rows:
        print("fpcalc failed to process any files (check codecs/files).", file=sys.stderr)
        return 1

    # Fingerprints TSV
    tsv_path = out_dir / "discog_audiofp.tsv"
    rows.sort(key=lambda x: x[2])
    with tsv_path.open("w", encoding="utf-8") as f:
        for dur, fp, p in rows:
            f.write(f"{dur}\t{fp}\t{p}\n")

    # release -> set(keys)
    release_keys: Dict[str, Set[TrackKey]] = defaultdict(set)
    for dur, fp, p in rows:
        rel = release_dir_from_path(Path(p))
        if not rel:
            continue
        release_keys[rel].add(TrackKey(dur, fp))

    releases = sorted(release_keys.keys())
    sizes = {r: len(release_keys[r]) for r in releases}

    track_to_releases: Dict[TrackKey, Set[str]] = defaultdict(set)
    for r in releases:
        for k in release_keys[r]:
            track_to_releases[k].add(r)

    unique_count = {
        r: sum(1 for k in release_keys[r] if len(track_to_releases[k]) == 1)
        for r in releases
    }

    # 1) exact duplicates (same set)
    by_set: Dict[frozenset, List[str]] = defaultdict(list)
    for r in releases:
        ks = release_keys[r]
        if ks:
            by_set[frozenset(ks)].append(r)

    duplicate_of: Dict[str, str] = {}
    canon_of_set: Dict[frozenset, str] = {}

    for aset, group in by_set.items():
        if len(group) <= 1:
            continue
        canon = sorted(group, key=lambda x: (-score_release(x), len(x), x))[0]
        canon_of_set[aset] = canon
        for g in group:
            if g != canon:
                duplicate_of[g] = canon

    # 2) subset contained in ONE other release
    contained_in: Dict[str, str] = {}

    for a in releases:
        if a in duplicate_of:
            continue
        A = release_keys[a]
        if not A:
            continue
        rare_track = min(A, key=lambda k: len(track_to_releases[k]))
        candidates = track_to_releases[rare_track] - {a}
        best = None
        for b in candidates:
            B = release_keys[b]
            if len(B) < len(A):
                continue
            if A.issubset(B):
                if best is None:
                    best = b
                else:
                    # Choose the smallest container, then prefer "best to keep"
                    if (sizes[b], -score_release(b), b) < (sizes[best], -score_release(best), best):
                        best = b
        if best is not None and best != a:
            contained_in[a] = best

    redundant: Set[str] = set(duplicate_of.keys())
    canons: Set[str] = set(canon_of_set.values())

    for a, b in contained_in.items():
        if a not in canons:
            redundant.add(a)

    # Safety check: do not remove a release with unique tracks
    unsafe = sorted([r for r in redundant if unique_count.get(r, 0) > 0])
    if unsafe:
        for r in unsafe:
            redundant.discard(r)

    # Post-check: do any subset relationships remain?
    remaining = [r for r in releases if r not in redundant and release_keys[r]]
    post_contained: List[Tuple[str, str]] = []
    for a in remaining:
        A = release_keys[a]
        for b in remaining:
            if b == a:
                continue
            B = release_keys[b]
            if A != B and A.issubset(B):
                post_contained.append((a, b))
                break

    # Write reports
    report_path = out_dir / "discog_redundancy_report.txt"
    list_path = out_dir / "discog_redundant_dirs.txt"
    post_path = out_dir / "discog_postcheck_contained.txt"

    lines: List[str] = []
    lines.append("=== DISCOGRAPHY REDUNDANCY REPORT (audio-content) ===\n")
    lines.append("Rule: remove a release only if ALL its tracks exist in ONE other release.\n")
    lines.append("Exact duplicates keep the best release (Albums > Singles, Deluxe/Edition preferred).\n\n")

    if unsafe:
        lines.append("!!! SAFETY: these releases were candidates but have unique tracks and are NOT removed:\n")
        for r in unsafe:
            lines.append(f"UNSAFE: {r}  unique_tracks={unique_count[r]}  total_tracks={sizes[r]}\n")
        lines.append("\n")

    if not redundant:
        lines.append("Nothing to remove: no releases fully covered by others.\n")
    else:
        dups = sorted([r for r in redundant if r in duplicate_of])
        subs = sorted([r for r in redundant if r not in duplicate_of])

        if dups:
            lines.append("== EXACT DUPLICATES (same track set) ==\n")
            for r in dups:
                lines.append(f"DELETE: {r}\n  identical_to: {duplicate_of[r]}\n  tracks: {sizes[r]}\n\n")

        if subs:
            lines.append("== FULLY CONTAINED (release is a subset of another release) ==\n")
            for r in subs:
                c = contained_in.get(r, "?")
                lines.append(
                    f"DELETE: {r}\n"
                    f"  contained_in: {c}\n"
                    f"  tracks: {sizes[r]} -> {sizes.get(c,'?')}\n"
                    f"  unique_tracks_in_release: {unique_count[r]}\n\n"
                )

    with report_path.open("w", encoding="utf-8") as f:
        f.write("".join(lines))

    with list_path.open("w", encoding="utf-8") as f:
        for r in sorted(redundant):
            f.write(r + "\n")

    with post_path.open("w", encoding="utf-8") as f:
        for a, b in post_contained:
            f.write(f"{a}\t<=\t{b}\n")

    # stdout summary
    if not args.quiet:
        print(f"Done. Reports in: {out_dir}")
        print(f"  - {report_path}")
        print(f"  - {list_path}")
        print(f"  - {post_path}")
        print(f"Candidates to remove/move: {len(redundant)}")
        if post_contained:
            print(f"Post-check: subset relationships remain: {len(post_contained)} (see {post_path})")
        else:
            print("Post-check: OK (no remaining A subset of B relationships).")

    # apply actions
    if args.move_to:
        dst = Path(args.move_to)
        ensure_dir(dst)
        moved = 0
        for r in sorted(redundant):
            src = Path(r)
            if src.exists():
                safe_move(src, dst)
                moved += 1
        if not args.quiet:
            print(f"Moved releases: {moved} -> {dst}")

    if args.delete:
        deleted = 0
        for r in sorted(redundant):
            src = Path(r)
            if src.exists():
                shutil.rmtree(src)
                deleted += 1
        if not args.quiet:
            print(f"Deleted releases: {deleted}")

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
