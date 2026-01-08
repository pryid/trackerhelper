#!/usr/bin/env python3
import argparse
import os
import sys
import json
import re
import subprocess
from pathlib import Path

AUDIO_EXTS_DEFAULT = {
    ".flac", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".wma", ".aiff", ".aif", ".alac"
}

PREFERRED_GROUP_ORDER = ["Albums", "Singles"]
GROUP_TITLES_RU = {
    "Albums": "Альбомы",
    "Singles": "Синглы",
}

# ---------- utils ----------

def which(cmd: str) -> str | None:
    for p in os.environ.get("PATH", "").split(os.pathsep):
        cand = Path(p) / cmd
        if cand.exists() and os.access(cand, os.X_OK):
            return str(cand)
    return None

def format_hhmmss(total_seconds: float) -> str:
    s = int(round(total_seconds))
    h = s // 3600
    s %= 3600
    m = s // 60
    s %= 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def format_khz(sr_hz: int) -> str:
    if sr_hz % 1000 == 0:
        return f"{sr_hz // 1000}"
    return f"{sr_hz / 1000:.1f}".rstrip("0").rstrip(".")

def track_word(n: int) -> str:
    return "track" if n == 1 else "tracks"

def release_word(n: int) -> str:
    return "release" if n == 1 else "releases"

def sr_label(srset: set[int]) -> str:
    if len(srset) == 1:
        return f"{format_khz(next(iter(srset)))} khz"
    if len(srset) > 1:
        return "mixed khz"
    return "unknown khz"

def bit_label(bitset: set[int]) -> str:
    if len(bitset) == 1:
        return f"{next(iter(bitset))} bit"
    if len(bitset) > 1:
        return "mixed bit"
    return "unknown bit"

def codec_label(exts: set[str]) -> str:
    if len(exts) == 1:
        e = next(iter(exts))
        return f"{e.lstrip('.').upper()} (*{e})"
    if len(exts) > 1:
        joined = "/".join(f"*{e}" for e in sorted(exts))
        return f"mixed ({joined})"
    return "unknown"

def group_key(rel_folder: Path) -> str:
    parts = rel_folder.parts
    return parts[0] if parts else "."

def group_sort_index(g: str) -> tuple[int, str]:
    if g in PREFERRED_GROUP_ORDER:
        return (PREFERRED_GROUP_ORDER.index(g), "")
    return (len(PREFERRED_GROUP_ORDER), g.lower())

def parse_release_title_and_year(folder_name: str) -> tuple[str, int | None]:
    m = re.match(r"^(.*?)(?:\s*[-–]\s*)(\d{4})\s*$", folder_name)
    if not m:
        return folder_name, None
    title = m.group(1).strip()
    try:
        year = int(m.group(2))
    except ValueError:
        year = None
    return (title if title else folder_name, year)

def extract_years_from_text(s: str) -> list[int]:
    return [int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", s)]

def ffprobe_info(file_path: Path) -> tuple[float | None, int | None, int | None]:
    """
    Returns (duration_seconds, sample_rate_hz, bit_depth)
    """
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration:stream=codec_type,sample_rate,bits_per_sample,bits_per_raw_sample",
                "-of", "json",
                str(file_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return (None, None, None)

        data = json.loads(proc.stdout)

        dur = None
        fmt = data.get("format", {}) or {}
        if "duration" in fmt:
            try:
                dur = float(fmt["duration"])
            except (ValueError, TypeError):
                dur = None

        sr = None
        bit = None
        for st in (data.get("streams") or []):
            if st.get("codec_type") != "audio":
                continue

            try:
                if st.get("sample_rate"):
                    sr = int(st["sample_rate"])
            except (ValueError, TypeError):
                sr = None

            b = st.get("bits_per_raw_sample") or st.get("bits_per_sample")
            try:
                if b is not None and str(b).strip() != "":
                    bit = int(b)
            except (ValueError, TypeError):
                bit = None
            break

        return (dur, sr, bit)

    except Exception:
        return (None, None, None)

def build_tracklist_lines(audio_files: list[Path]) -> list[str]:
    lines: list[str] = []
    auto_n = 1

    for f in sorted(audio_files):
        stem = f.stem
        m = re.match(r"^\s*(\d{1,3})\s*([.\-_\s]+)\s*(.*)$", stem)
        if m:
            num = m.group(1)
            title = m.group(3).strip() or stem
            width = 3 if len(num) >= 3 else 2
            num_fmt = f"{int(num):0{width}d}"
        else:
            num_fmt = f"{auto_n:02d}"
            title = stem.strip() or stem
            auto_n += 1

        title = re.sub(r"\s+", " ", title).strip()
        lines.append(f"{num_fmt}. {title}")

    return lines

# ---------- DR helpers ----------

def normalize_name(s: str) -> str:
    s = s.strip().lower()
    s = s.replace("ё", "е")
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", " ", s)
    return s

def strip_dr_suffix(stem: str) -> str:
    s = stem
    s = re.sub(r"[\s._-]*(dr|d\.r\.)\s*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*\(dr\)\s*$", "", s, flags=re.IGNORECASE)
    return s.strip()

def read_text_guess(path: Path) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
        except Exception:
            break
    return path.read_text(encoding="utf-8", errors="replace")

def build_dr_index(dr_dir: Path) -> dict[str, Path]:
    idx: dict[str, Path] = {}
    if not dr_dir.exists() or not dr_dir.is_dir():
        return idx

    for p in dr_dir.iterdir():
        if not p.is_file() or p.suffix.lower() != ".txt":
            continue
        key = normalize_name(strip_dr_suffix(p.stem))
        if key and key not in idx:
            idx[key] = p
    return idx

def find_dr_text_for_release(folder_name: str, dr_dir: Path, dr_index: dict[str, Path]) -> str | None:
    candidates = [
        dr_dir / f"{folder_name}_dr.txt",
        dr_dir / f"{folder_name}-dr.txt",
        dr_dir / f"{folder_name} - dr.txt",
        dr_dir / f"{folder_name} DR.txt",
        dr_dir / f"{folder_name}_DR.txt",
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return read_text_guess(c).rstrip("\n")

    key = normalize_name(folder_name)
    p = dr_index.get(key)
    if p and p.exists():
        return read_text_guess(p).rstrip("\n")

    return None

# ---------- release bbcode ----------

def make_release_bbcode(
    root_name: str,
    year_range: str | None,
    total_duration: str,
    overall_codec: str,
    overall_bit: str,
    overall_sr: str,
    grouped_releases: dict[str, list[dict]],
) -> str:
    yr = f" - {year_range}" if year_range else ""
    parts: list[str] = []

    parts.append(f"[size=24]{root_name}{yr}[/size]\n\n")
    parts.append("[img=right]ROOT_COVER_URL[/img]\n\n")
    parts.append("[b]Жанр[/b]: GENRE\n")
    parts.append("[b]Носитель[/b]: WEB SOURCE\n")
    parts.append(f"[b]Год издания[/b]: {year_range or 'YEAR'}\n")
    parts.append(f"[b]Аудиокодек[/b]: {overall_codec}\n")
    parts.append("[b]Тип рипа[/b]: tracks\n")
    parts.append(f"[b]Продолжительность[/b]: {total_duration}\n")

    for group in sorted(grouped_releases.keys(), key=group_sort_index):
        ru_title = GROUP_TITLES_RU.get(group, group)
        parts.append(f'[spoiler="{ru_title}"]\n\n')

        for rel in grouped_releases[group]:
            year = rel["year"]
            title = rel["title"]
            spoiler_title = f"[{year}] {title}" if year else title

            parts.append(f'[spoiler="{spoiler_title}"]\n')
            parts.append("[align=center]")
            parts.append(f"Продолжительность: {rel['duration']}\n")
            parts.append('[spoiler="Треклист"]\n')
            parts.extend(line + "\n" for line in rel["tracklist"])
            parts.append("[/spoiler]\n")
            parts.append("[/align]\n\n")

            parts.append('[spoiler="Динамический отчет (DR)"]\n')
            parts.append(((rel.get("dr") or "info").rstrip("\n")) + "\n")
            parts.append("[/spoiler]\n")
            parts.append("[/spoiler]\n\n")

        parts.append("[/spoiler]\n\n")

    parts.append('[spoiler="Об исполнителе (группе)"]\n')
    parts.append("info\n")
    parts.append("[/spoiler]\n")

    return "".join(parts)

# ---------- main ----------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Sum durations grouped per release folder; show bit depth + sample rate; optionally generate BBCode release template."
    )
    ap.add_argument("path", nargs="?", default=".", help="Root folder (default: current directory).")
    ap.add_argument("--ext", action="append", default=[], help="Add extension (e.g. --ext .flac). Repeatable.")
    ap.add_argument("--include-root", action="store_true", help="Include tracks directly inside the root folder.")
    ap.add_argument("--flat", action="store_true", help="Flat output without group headers (Albums/Singles).")
    ap.add_argument("--release", action="store_true", help="Write BBCode release template to /tmp/<root_folder_name>.")
    ap.add_argument("--dr", default=None, help="Directory with DR reports (e.g. *_dr.txt). Use with --release.")
    args = ap.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"Error: '{root}' is not a directory.", file=sys.stderr)
        return 2

    if which("ffprobe") is None:
        print("Error: ffprobe not found. Install ffmpeg (ffprobe) and retry.", file=sys.stderr)
        return 3

    exts = set(AUDIO_EXTS_DEFAULT)
    for e in args.ext:
        e = e.strip().lower()
        if e and not e.startswith("."):
            e = "." + e
        if e:
            exts.add(e)

    dr_dir: Path | None = None
    dr_index: dict[str, Path] = {}
    if args.dr is not None:
        dr_dir = Path(args.dr).expanduser().resolve()
        if not dr_dir.exists() or not dr_dir.is_dir():
            print(f"Warning: --dr path is not a directory: {dr_dir}", file=sys.stderr)
            dr_dir = None
        else:
            dr_index = build_dr_index(dr_dir)

    # per-release(folder) stats
    per_dir_seconds: dict[Path, float] = {}
    per_dir_count: dict[Path, int] = {}
    per_dir_sr: dict[Path, set[int]] = {}
    per_dir_bit: dict[Path, set[int]] = {}
    per_dir_exts: dict[Path, set[str]] = {}
    per_dir_files: dict[Path, list[Path]] = {}

    total_seconds = 0.0
    total_tracks = 0
    total_sr: set[int] = set()
    total_bit: set[int] = set()
    total_exts: set[str] = set()
    all_years: list[int] = []

    for dirpath, _, filenames in os.walk(root):
        d = Path(dirpath)
        if d == root and not args.include_root:
            continue

        audio_files: list[Path] = []
        for fn in filenames:
            p = d / fn
            if p.is_file() and p.suffix.lower() in exts:
                audio_files.append(p)

        if not audio_files:
            continue

        folder_sum = 0.0
        folder_tracks = 0
        sr_set: set[int] = set()
        bit_set: set[int] = set()
        ext_set: set[str] = set()

        for f in sorted(audio_files):
            dur, sr, bit = ffprobe_info(f)
            if dur is None:
                print(f"Warning: can't read duration: {f}", file=sys.stderr)
                continue

            folder_sum += dur
            folder_tracks += 1

            if sr is not None:
                sr_set.add(sr)
                total_sr.add(sr)
            if bit is not None:
                bit_set.add(bit)
                total_bit.add(bit)

            ext_set.add(f.suffix.lower())
            total_exts.add(f.suffix.lower())

        if folder_tracks > 0:
            per_dir_seconds[d] = per_dir_seconds.get(d, 0.0) + folder_sum
            per_dir_count[d] = per_dir_count.get(d, 0) + folder_tracks
            per_dir_sr.setdefault(d, set()).update(sr_set)
            per_dir_bit.setdefault(d, set()).update(bit_set)
            per_dir_exts.setdefault(d, set()).update(ext_set)
            per_dir_files[d] = sorted(audio_files)

            total_seconds += folder_sum
            total_tracks += folder_tracks

            rel = d.relative_to(root)
            all_years.extend(extract_years_from_text(rel.as_posix()))

    if not per_dir_seconds:
        print("No audio files found.")
        return 0

    total_releases = len(per_dir_seconds)

    # console items
    items = []
    for folder_abs, secs in per_dir_seconds.items():
        rel = folder_abs.relative_to(root)
        cnt = per_dir_count.get(folder_abs, 0)
        srset = per_dir_sr.get(folder_abs, set())
        bitset = per_dir_bit.get(folder_abs, set())
        items.append((rel, secs, cnt, srset, bitset))

    items.sort(key=lambda x: (group_sort_index(group_key(x[0])), x[0].as_posix().lower()))

    # console output
    if args.flat:
        for rel, secs, cnt, srset, bitset in items:
            print(
                f"{rel.as_posix()} - {format_hhmmss(secs)} "
                f"({cnt} {track_word(cnt)}, {bit_label(bitset)}, {sr_label(srset)})"
            )
    else:
        current_group = None
        for rel, secs, cnt, srset, bitset in items:
            g = group_key(rel)
            if g != current_group:
                if current_group is not None:
                    print()
                print(f"{g}:")
                current_group = g

            pretty = Path(*rel.parts[1:]).as_posix() if len(rel.parts) > 1 else rel.as_posix()
            print(
                f"  {pretty} - {format_hhmmss(secs)} "
                f"({cnt} {track_word(cnt)}, {bit_label(bitset)}, {sr_label(srset)})"
            )

    print(
        f"\nTotal: {format_hhmmss(total_seconds)} "
        f"({total_tracks} {track_word(total_tracks)}, {total_releases} {release_word(total_releases)})"
    )

    # ---------- --release ----------
    if args.release:
        year_range = None
        if all_years:
            y_min, y_max = min(all_years), max(all_years)
            year_range = f"{y_min}–{y_max}" if y_min != y_max else f"{y_min}"

        grouped: dict[str, list[dict]] = {}
        for folder_abs in per_dir_seconds.keys():
            rel = folder_abs.relative_to(root)
            g = group_key(rel)

            folder_name = folder_abs.name
            title, year = parse_release_title_and_year(folder_name)

            files = per_dir_files.get(folder_abs, [])
            tracklist = build_tracklist_lines(files)

            dr_text = None
            if dr_dir is not None:
                dr_text = find_dr_text_for_release(folder_name, dr_dir, dr_index)

            grouped.setdefault(g, []).append(
                {
                    "title": title,
                    "year": year,
                    "duration": format_hhmmss(per_dir_seconds[folder_abs]),
                    "tracklist": tracklist,
                    "dr": dr_text,
                }
            )

        for g, lst in grouped.items():
            lst.sort(key=lambda r: ((r["year"] or 9999), str(r["title"]).lower()))

        bbcode = make_release_bbcode(
            root_name=root.name,
            year_range=year_range,
            total_duration=format_hhmmss(total_seconds),
            overall_codec=codec_label(total_exts),
            overall_bit=bit_label(total_bit),
            overall_sr=sr_label(total_sr),
            grouped_releases=grouped,
        )

        out_path = Path("/tmp") / root.name  # без расширения
        out_path.write_text(bbcode, encoding="utf-8")
        print(f"\nWrote release template: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
