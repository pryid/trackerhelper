#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
discog_dedupe_audio.py

Найти релизы, которые полностью дублируют контент (по звуку) других релизов.
Работает по акустическим отпечаткам Chromaprint (fpcalc), метаданные/обложки не учитываются.

Правила:
- Релиз можно убрать, только если ВСЕ его треки (duration+fingerprint) содержатся в ОДНОМ другом релизе.
- Точные дубли релизов (одинаковый набор треков) -> оставить "лучший", остальные убрать.
- Если у релиза есть уникальные треки, он не должен попасть в удаление (есть safety-check).

По умолчанию: ничего не удаляет, только пишет отчёты.
Опционально: --move-to DIR (переместить кандидатов), либо --delete (удалить).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
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
        print(f"ERROR: не найдено '{cmd}' в PATH. Установи пакет chromaprint (fpcalc).", file=sys.stderr)
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
    Возвращает (duration, fingerprint, filepath) или None если fpcalc не смог.
    """
    try:
        # fpcalc выводит строки вида:
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
    Считает релизом папку первого уровня под Albums/ или Singles/.
    Пример: Albums/Clams Casino - Moon Trip Radio - 2019/01 - ... -> Albums/Clams Casino - Moon Trip Radio - 2019
    """
    parts = p.parts
    if "Albums" in parts:
        i = parts.index("Albums")
    elif "Singles" in parts:
        i = parts.index("Singles")
    else:
        return None
    if i + 1 >= len(parts):
        return None
    return str(Path(*parts[: i + 2]))


def score_release(rel: str) -> int:
    """
    Эвристика "что лучше оставить", если одинаковый контент.
    """
    s = rel.lower()
    sc = 0
    if s.startswith("albums/"):
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
    Перемещает src внутрь dst_dir. Если имя занято, добавит суффикс времени.
    """
    ensure_dir(dst_dir)
    target = dst_dir / src.name
    if target.exists():
        suffix = time.strftime("%Y%m%d-%H%M%S")
        target = dst_dir / f"{src.name}__{suffix}"
    shutil.move(str(src), str(target))
    return target


def main() -> int:
    which_or_die("fpcalc")

    ap = argparse.ArgumentParser(
        description="Удаление релизов-дублей по содержанию звука (Chromaprint/fpcalc)."
    )
    ap.add_argument(
        "--roots",
        nargs="*",
        default=["Albums", "Singles"],
        help="Корневые папки для сканирования (по умолчанию: Albums Singles).",
    )
    ap.add_argument(
        "--ext",
        nargs="*",
        default=sorted(AUDIO_EXTS_DEFAULT),
        help="Список расширений аудио (по умолчанию: распространённые).",
    )
    ap.add_argument(
        "--out-dir",
        default="_dedupe_reports",
        help="Куда писать отчёты (по умолчанию: ./_dedupe_reports).",
    )
    ap.add_argument(
        "--jobs",
        type=int,
        default=max(1, (os.cpu_count() or 2)),
        help="Параллельность при fpcalc (по умолчанию: cpu_count).",
    )
    ap.add_argument(
        "--move-to",
        default=None,
        help="Если задано: переместить найденные релизы в указанную папку (без удаления).",
    )
    ap.add_argument(
        "--delete",
        action="store_true",
        help="Если задано: удалить найденные релизы (ОПАСНО).",
    )
    ap.add_argument(
        "--quiet",
        action="store_true",
        help="Меньше вывода в stdout.",
    )

    args = ap.parse_args()

    if args.delete and args.move_to:
        print("ERROR: нельзя одновременно --delete и --move-to", file=sys.stderr)
        return 2

    roots = [Path(r) for r in args.roots]
    exts = {e.lower() if e.startswith(".") else "." + e.lower() for e in args.ext}
    out_dir = Path(args.out_dir)
    ensure_dir(out_dir)

    audio_files = list(iter_audio_files(roots, exts))
    if not audio_files:
        print("Не найдено аудиофайлов в указанных roots.", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"Найдено аудиофайлов: {len(audio_files)}")
        print(f"Считаю отпечатки fpcalc (jobs={args.jobs})...")

    # Параллельный fpcalc через multiprocessing (без внешних зависимостей)
    from multiprocessing import Pool

    rows: List[Tuple[str, str, str]] = []
    with Pool(processes=args.jobs) as pool:
        for r in pool.imap_unordered(fpcalc_one, audio_files, chunksize=8):
            if r is not None:
                rows.append(r)

    if not rows:
        print("fpcalc не смог обработать ни один файл (проверь кодеки/файлы).", file=sys.stderr)
        return 1

    # TSV отпечатков
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

    # Сколько раз каждый трек встречается
    track_counts = Counter()
    for r in releases:
        track_counts.update(release_keys[r])

    unique_count = {r: sum(1 for k in release_keys[r] if track_counts[k] == 1) for r in releases}

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
        best = None
        for b in releases:
            if b == a:
                continue
            B = release_keys[b]
            if len(B) < len(A):
                continue
            if A.issubset(B):
                if best is None:
                    best = b
                else:
                    # выбираем минимальный контейнер, затем "лучше оставить"
                    if (len(B), -score_release(b), b) < (len(release_keys[best]), -score_release(best), best):
                        best = b
        if best is not None and best != a:
            contained_in[a] = best

    redundant: Set[str] = set(duplicate_of.keys())
    canons: Set[str] = set(canon_of_set.values())

    for a, b in contained_in.items():
        if a not in canons:
            redundant.add(a)

    # Safety-check: не удалять релиз с уникальными треками
    unsafe = sorted([r for r in redundant if unique_count.get(r, 0) > 0])
    if unsafe:
        for r in unsafe:
            redundant.discard(r)

    # Пост-проверка: среди оставшихся релизов есть ли subset-отношения?
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

    # Запись отчётов
    report_path = out_dir / "discog_redundancy_report.txt"
    list_path = out_dir / "discog_redundant_dirs.txt"
    post_path = out_dir / "discog_postcheck_contained.txt"

    lines: List[str] = []
    lines.append("=== DISCOGRAPHY REDUNDANCY REPORT (audio-content) ===\n")
    lines.append("Правило: удаляем релиз только если ВСЕ его треки по звуку есть в ОДНОМ другом релизе,\n")
    lines.append("и удаляем точные дубли релизов, оставляя лучший (Albums > Singles, Deluxe/Edition предпочтительнее).\n\n")

    if unsafe:
        lines.append("!!! SAFETY: эти релизы были кандидаты, но у них есть уникальные треки — НЕ УДАЛЯЮТСЯ:\n")
        for r in unsafe:
            lines.append(f"UNSAFE: {r}  unique_tracks={unique_count[r]}  total_tracks={sizes[r]}\n")
        lines.append("\n")

    if not redundant:
        lines.append("Нечего удалять: нет релизов, полностью покрытых другими.\n")
    else:
        dups = sorted([r for r in redundant if r in duplicate_of])
        subs = sorted([r for r in redundant if r not in duplicate_of])

        if dups:
            lines.append("== EXACT DUPLICATES (одинаковый набор треков) ==\n")
            for r in dups:
                lines.append(f"DELETE: {r}\n  identical_to: {duplicate_of[r]}\n  tracks: {sizes[r]}\n\n")

        if subs:
            lines.append("== FULLY CONTAINED (релиз является подмножеством одного другого релиза) ==\n")
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
            f.write(f"{a}\t⊆\t{b}\n")

    # stdout summary
    if not args.quiet:
        print(f"Готово. Отчёты в: {out_dir}")
        print(f"  - {report_path}")
        print(f"  - {list_path}")
        print(f"  - {post_path}")
        print(f"Кандидатов на удаление/перемещение: {len(redundant)}")
        if post_contained:
            print(f"Пост-проверка: среди оставшихся ещё есть subset-отношения: {len(post_contained)} (см. {post_path})")
        else:
            print("Пост-проверка: OK (среди оставшихся нет отношений A ⊆ B).")

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
            print(f"Перемещено релизов: {moved} -> {dst}")

    if args.delete:
        deleted = 0
        for r in sorted(redundant):
            src = Path(r)
            if src.exists():
                shutil.rmtree(src)
                deleted += 1
        if not args.quiet:
            print(f"Удалено релизов: {deleted}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
