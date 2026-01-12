#!/usr/bin/env python3
"""
Скрипт для подсчёта общей длительности аудио по папкам-релизам и генерации BBCode-шаблона раздачи.

Основная идея:
- Каждый релиз — это папка, в которой лежат аудиофайлы.
- Скрипт суммирует длительность треков в каждой папке (через ffprobe),
  считает количество треков, собирает sample rate / bit depth / расширения.
- Опционально генерирует BBCode-шаблон раздачи (структура BBCode должна оставаться неизменной).

Примечание:
- Опция --test оставлена для проверки форматирования вывода без доступа к файловой системе/ffprobe,
  но тестовые данные вынесены в отдельный файл synthetic_dataset.py.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable

import shutil

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore

# Поддерживаемые расширения аудиофайлов по умолчанию
AUDIO_EXTS_DEFAULT = {
    ".flac", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".wma", ".aiff", ".aif", ".alac"
}

# Порядок групп для красивого вывода/BBCode
PREFERRED_GROUP_ORDER = ["Albums", "Singles"]
GROUP_TITLES_RU = {
    "Albums": "Альбомы",
    "Singles": "Синглы",
}

# ----------------------------
# Cover upload (FastPic)
# ----------------------------

class FastPicUploadError(RuntimeError):
    pass


def upload_to_fastpic_get_direct_link(
    file_path: Path,
    *,
    resize_to: int = 500,  # "Уменьшить до 500" на стороне сайта
    endpoint: str = "https://fastpic.org/upload?api=1",
    timeout: int = 60,
    session=None,
) -> str:
    """Загружает картинку на FastPic и возвращает Direct Link (<imagepath>).

    ВАЖНО: функция НЕ ресайзит картинку локально — ресайз делает FastPic.
    """
    if requests is None:
        raise RuntimeError("Cover upload requires 'requests'. Install it or run without --release cover upload.")

    if not file_path.is_file():
        raise FileNotFoundError(file_path)

    s = session or requests.Session()

    data = {
        "method": "file",
        "uploading": "1",
        "check_thumb": "no",
        # ресайз на стороне fastpic:
        "check_orig_resize": "1",
        "orig_resize": str(int(resize_to)),
    }

    with file_path.open("rb") as f:
        resp = s.post(endpoint, data=data, files={"file1": f}, timeout=timeout)
    resp.raise_for_status()

    # FastPic отвечает XML
    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as e:
        raise FastPicUploadError(
            f"Не смог распарсить XML-ответ: {e}. Ответ: {resp.text[:300]!r}"
        ) from e

    err = root.findtext("error")
    if err:
        raise FastPicUploadError(f"FastPic вернул ошибку: {err}")

    direct = root.findtext("imagepath")  # Direct Link
    if not direct:
        raise FastPicUploadError(f"В ответе нет <imagepath>. Ответ: {resp.text[:500]!r}")

    return direct.strip()


class FastPicCoverUploader:
    """Uploader с переиспользованием Session и простым in-memory кешем."""

    def __init__(
        self,
        *,
        resize_to: int = 500,
        endpoint: str = "https://fastpic.org/upload?api=1",
        timeout: int = 60,
    ) -> None:
        if requests is None:
            raise RuntimeError("FastPicCoverUploader requires 'requests'")
        self.resize_to = int(resize_to)
        self.endpoint = endpoint
        self.timeout = int(timeout)
        self.session = requests.Session()
        self._cache: dict[str, str] = {}

    def upload(self, file_path: Path) -> str:
        key = str(file_path.resolve())
        if key in self._cache:
            return self._cache[key]

        url = upload_to_fastpic_get_direct_link(
            file_path,
            resize_to=self.resize_to,
            endpoint=self.endpoint,
            timeout=self.timeout,
            session=self.session,
        )
        self._cache[key] = url
        return url


def find_cover_jpg(release_folder: Path) -> Path | None:
    """Ищем cover.jpg в папке релиза (case-insensitive)."""
    p = release_folder / "cover.jpg"
    if p.is_file():
        return p

    try:
        for child in release_folder.iterdir():
            if child.is_file() and child.name.lower() == "cover.jpg":
                return child
    except FileNotFoundError:
        return None

    return None


# ----------------------------
# Утилиты форматирования/лейблы
# ----------------------------

def which(cmd: str) -> str | None:
    """Возвращает путь к исполняемому файлу в PATH или None."""
    return shutil.which(cmd)

def format_hhmmss(total_seconds: float) -> str:
    """Форматирует секунды в HH:MM:SS."""
    s = int(round(total_seconds))
    h = s // 3600
    s %= 3600
    m = s // 60
    s %= 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def format_khz(sr_hz: int) -> str:
    """Sample rate в kHz (как в оригинальной логике)."""
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

# ----------------------------
# Группировка/сортировка релизов
# ----------------------------

def group_key(rel_folder: Path) -> str:
    """Группа = первый сегмент относительного пути (Albums/Singles/и т.п.)."""
    parts = rel_folder.parts
    return parts[0] if parts else "."

def group_sort_index(g: str) -> tuple[int, str]:
    """Сортировка групп: сначала PREFERRED_GROUP_ORDER, потом по алфавиту."""
    if g in PREFERRED_GROUP_ORDER:
        return (PREFERRED_GROUP_ORDER.index(g), "")
    return (len(PREFERRED_GROUP_ORDER), g.lower())

def parse_release_title_and_year(folder_name: str) -> tuple[str, int | None]:
    """
    Пытается распарсить "Title - 2020" или "Title – 2020".
    Возвращает (title, year|None).
    """
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
    """Находим годы в любом тексте (используется для year_range по структуре папок)."""
    return [int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", s)]

_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")

def clean_name_part(s: str) -> str:
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def normalize_tag_key(s: str) -> str:
    return re.sub(r"\s+", "_", s.strip().lower())

def ffprobe_tags(file_path: Path) -> dict[str, str]:
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format_tags",
                "-of", "json",
                str(file_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return {}

        data = json.loads(proc.stdout)
        tags_raw = (data.get("format") or {}).get("tags") or {}
        tags: dict[str, str] = {}
        for k, v in tags_raw.items():
            if v is None:
                continue
            key = normalize_tag_key(str(k))
            val = str(v).strip()
            if key and val:
                tags[key] = val
        return tags
    except Exception:
        return {}

def tag_value(tags: dict[str, str], keys: list[str]) -> str | None:
    for k in keys:
        v = tags.get(k)
        if v:
            return v.strip()
    return None

def most_common_str(values: list[str]) -> str | None:
    if not values:
        return None
    counts: dict[str, int] = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    return max(counts.items(), key=lambda x: (x[1], -len(x[0]), x[0].lower()))[0]

def parse_year_from_folder_name(name: str) -> int | None:
    years = [int(m.group(1)) for m in _YEAR_RE.finditer(name)]
    return years[-1] if years else None

def release_metadata_from_tags(audio_files: list[Path]) -> tuple[str | None, str | None]:
    album_values: list[str] = []
    album_artist_values: list[str] = []
    artist_values: list[str] = []

    for f in audio_files:
        tags = ffprobe_tags(f)
        if not tags:
            continue

        album = tag_value(tags, ["album"])
        if album:
            album_values.append(clean_name_part(album))

        album_artist = tag_value(tags, ["album_artist", "albumartist"])
        if album_artist:
            album_artist_values.append(clean_name_part(album_artist))

        artist = tag_value(tags, ["artist", "performer"])
        if artist:
            artist_values.append(clean_name_part(artist))

    album = most_common_str(album_values)
    artist = most_common_str(album_artist_values) or most_common_str(artist_values)
    return artist, album

def normalize_release_folders(root: Path, exts: set[str], apply: bool) -> int:
    release_data = [
        (folder, files)
        for folder, files in iter_release_audio_files(root, exts, include_root=True)
    ]
    release_data.sort(key=lambda x: x[0].as_posix().lower())

    if not release_data:
        print("No audio files found for normalization.")
        return 0

    single_mode = len(release_data) == 1
    if not single_mode:
        release_data = [(f, files) for f, files in release_data if f != root]
        if not release_data:
            single_mode = True
            release_data = [(root, [])]

    actions: list[tuple[Path, Path]] = []
    planned_targets: set[Path] = set()
    def display_path(p: Path) -> str:
        if p == root or p.parent == root.parent:
            return p.name
        try:
            rel = p.relative_to(root)
        except ValueError:
            return p.as_posix()
        return p.name if str(rel) == "." else rel.as_posix()

    for folder, files in release_data:
        artist, album = release_metadata_from_tags(files)
        year = parse_year_from_folder_name(folder.name)

        if single_mode:
            if year is None or not artist or not album:
                print(
                    f"Skip: can't normalize '{folder.name}' (missing tags/year).",
                    file=sys.stderr,
                )
                continue

            new_name = f"{artist} - {album} ({year})"
            new_name = clean_name_part(new_name)
        else:
            if year is None or not artist or not album:
                print(
                    f"Skip: can't normalize '{folder.name}' (missing tags/year).",
                    file=sys.stderr,
                )
                continue
            new_name = f"{year} - {artist} - {album}"
            new_name = clean_name_part(new_name)

        target = folder.with_name(new_name)
        if target == folder:
            continue

        if target in planned_targets:
            print(f"Skip: duplicate target '{target.name}'.", file=sys.stderr)
            continue

        if target.exists() and target != folder:
            print(f"Skip: target exists '{target}'.", file=sys.stderr)
            continue

        planned_targets.add(target)
        actions.append((folder, target))

    if not actions:
        print("Nothing to normalize.")
        return 0

    if not apply:
        print("Dry run (use --normalize --y to apply):")
        for src, dst in actions:
            print(f"  {display_path(src)} -> {display_path(dst)}")
        return len(actions)

    for src, dst in actions:
        src.rename(dst)
        print(f"Renamed: {display_path(src)} -> {display_path(dst)}")

    return len(actions)

# ----------------------------
# Работа с ffprobe
# ----------------------------

def ffprobe_info(file_path: Path) -> tuple[float | None, int | None, int | None]:
    """
    Возвращает (duration_seconds, sample_rate_hz, bit_depth).

    Важно:
    - duration берём из format.duration
    - sr/bit берём из первого audio-stream
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

# ----------------------------
# Треклист
# ----------------------------

_TRACK_NUM_RE = re.compile(r"^\s*(\d{1,3})\s*([.\-_\s]+)\s*(.*)$")

def build_tracklist_lines(audio_files: list[Path]) -> list[str]:
    """
    Делает треклист по именам файлов.

    Логика оставлена прежней:
    - Если имя начинается с номера, используем его.
    - Иначе нумеруем автоматически с 01.
    """
    lines: list[str] = []
    auto_n = 1

    for f in sorted(audio_files):
        stem = f.stem
        m = _TRACK_NUM_RE.match(stem)
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

# ----------------------------
# DR helpers (поиск и чтение отчётов)
# ----------------------------

def normalize_name(s: str) -> str:
    """Нормализация для сопоставления названий релизов с DR-файлами."""
    s = s.strip().lower()
    s = s.replace("ё", "е")
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", " ", s)
    return s

def strip_dr_suffix(stem: str) -> str:
    """Убирает суффиксы вида _dr, -dr, (dr) и т.п. из имени файла (без расширения)."""
    s = stem
    s = re.sub(r"[\s._-]*(dr|d\.r\.)\s*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*\(dr\)\s*$", "", s, flags=re.IGNORECASE)
    return s.strip()

def read_text_guess(path: Path) -> str:
    """
    Пытаемся прочитать текст в распространённых кодировках.
    Полезно для отчётов DR, которые иногда бывают в cp1251.
    """
    for enc in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
        except Exception:
            break
    return path.read_text(encoding="utf-8", errors="replace")

def build_dr_index(dr_dir: Path) -> dict[str, Path]:
    """
    Индекс: normalized_release_name -> путь к txt.
    Нужен как fallback, если файл не совпал по точному имени.
    """
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
    """
    Поиск DR-отчёта для папки релиза.

    Сначала пробуем "как в оригинале" через несколько шаблонов,
    затем — через индекс normalize_name.
    """
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

# ----------------------------
# BBCode генерация
# ----------------------------

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
    parts.append("[b]Носитель[/b]: WEB [url=https://service.com/123]Service[/url]\n")
    parts.append("[b]Издатель (лейбл)[/b]: ЛЕЙБЛ\n")
    parts.append(f"[b]Год издания[/b]: {year_range or 'YEAR'}\n")
    parts.append(f"[b]Аудиокодек[/b]: {overall_codec}\n")
    parts.append("[b]Тип рипа[/b]: tracks\n")
    parts.append("[b]Источник[/b]: WEB\n")
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
            cover = rel.get("cover_url") or "COVER_URL"
            parts.append(f"[img]{cover}[/img]\n")
            parts.append("[b]Носитель[/b]: WEB [url=https://service.com/123]Service[/url]\n")
            parts.append(f"Продолжительность: {rel['duration']}\n")
            parts.append('[spoiler="Треклист"]\n')
            parts.extend(line + "\n" for line in rel["tracklist"])
            parts.append("[/spoiler]\n")
            parts.append("[/align]\n\n")

            parts.append('[spoiler="Динамический отчет (DR)"]\n')
            parts.append("[pre]\n")
            parts.append(((rel.get("dr") or "info").rstrip("\n")) + "\n")
            parts.append("[/pre]\n")
            parts.append("[/spoiler]\n")
            parts.append("[/spoiler]\n\n")

        parts.append("[/spoiler]\n\n")

    parts.append('[spoiler="Об исполнителе (группе)"]\n')
    parts.append("info\n")
    parts.append("[/spoiler]\n")

    return "".join(parts)

def make_single_release_bbcode(
    root_name: str,
    year_range: str | None,
    overall_codec: str,
    release: dict,
) -> str:
    title = str(release.get("title") or "").strip() or "TITLE"
    year_val = release.get("year") or year_range or "YEAR"
    cover = release.get("cover_url") or "COVER_URL"
    duration = release.get("duration") or "00:00:00"
    tracklist = release.get("tracklist") or []
    dr_text = (release.get("dr") or "info").rstrip("\n")

    parts: list[str] = []
    parts.append(f"[size=24]{root_name} / {title}[/size]\n\n")
    parts.append(f"[img=right]{cover}[/img]\n\n")
    parts.append("[b]Жанр[/b]: GENRE\n")
    parts.append("[b]Носитель[/b]: WEB [url=https://service.com/123]Service[/url]\n")
    parts.append("[b]Издатель (лейбл)[/b]: ЛЕЙБЛ\n")
    parts.append(f"[b]Год издания[/b]: {year_val}\n")
    parts.append(f"[b]Аудиокодек[/b]: {overall_codec}\n")
    parts.append("[b]Тип рипа[/b]: tracks\n")
    parts.append("[b]Источник[/b]: WEB\n")
    parts.append(f"[b]Продолжительность[/b]: {duration}\n\n")

    parts.append('[spoiler="Треклист"]\n')
    parts.extend(line + "\n" for line in tracklist)
    parts.append("[/spoiler]\n\n")

    parts.append('[spoiler="Динамический отчет (DR)"]\n')
    parts.append("[pre]\n")
    parts.append(dr_text + "\n")
    parts.append("[/pre]\n")
    parts.append("[/spoiler]\n\n")

    parts.append('[spoiler="Об исполнителе (группе)"]\n')
    parts.append("info\n")
    parts.append("[/spoiler]\n")

    return "".join(parts)

# ----------------------------
# Сбор данных
# ----------------------------

def iter_release_audio_files(root: Path, exts: set[str], include_root: bool) -> Iterable[tuple[Path, list[Path]]]:
    """
    Итерируемся по папкам и отдаём список аудиофайлов внутри папки.

    Важно:
    - В --release треклист строится по списку найденных файлов в папке (даже если ffprobe
      не смог прочитать длительность у какого-то файла — как в оригинале).
    """
    for dirpath, _, filenames in os.walk(root):
        folder = Path(dirpath)
        if folder == root and not include_root:
            continue

        audio_files: list[Path] = []
        for fn in filenames:
            p = folder / fn
            if p.is_file() and p.suffix.lower() in exts:
                audio_files.append(p)

        if audio_files:
            yield folder, sorted(audio_files)

def collect_real_stats(
    root: Path,
    exts: set[str],
    include_root: bool,
) -> tuple[
    dict[Path, float],
    dict[Path, int],
    dict[Path, set[int]],
    dict[Path, set[int]],
    dict[Path, set[str]],
    dict[Path, list[Path]],
    float,
    int,
    set[int],
    set[int],
    set[str],
    list[int],
]:
    """
    Собирает статистику с реальной ФС + ffprobe.

    Возвращаем те же структуры, что и в исходном коде, чтобы снизить риск
    "случайно поменять логику".
    """
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

    for folder, audio_files in iter_release_audio_files(root, exts, include_root):
        folder_sum = 0.0
        folder_tracks = 0
        sr_set: set[int] = set()
        bit_set: set[int] = set()
        ext_set: set[str] = set()

        for f in audio_files:
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
            per_dir_seconds[folder] = per_dir_seconds.get(folder, 0.0) + folder_sum
            per_dir_count[folder] = per_dir_count.get(folder, 0) + folder_tracks
            per_dir_sr.setdefault(folder, set()).update(sr_set)
            per_dir_bit.setdefault(folder, set()).update(bit_set)
            per_dir_exts.setdefault(folder, set()).update(ext_set)
            per_dir_files[folder] = audio_files  # список всех найденных файлов

            total_seconds += folder_sum
            total_tracks += folder_tracks

            rel = folder.relative_to(root)
            all_years.extend(extract_years_from_text(rel.as_posix()))

    return (
        per_dir_seconds,
        per_dir_count,
        per_dir_sr,
        per_dir_bit,
        per_dir_exts,
        per_dir_files,
        total_seconds,
        total_tracks,
        total_sr,
        total_bit,
        total_exts,
        all_years,
    )

def collect_synthetic_stats(
    root: Path,
) -> tuple[
    dict[Path, float],
    dict[Path, int],
    dict[Path, set[int]],
    dict[Path, set[int]],
    dict[Path, set[str]],
    dict[Path, list[Path]],
    dict[Path, str | None],
    float,
    int,
    set[int],
    set[int],
    set[str],
    list[int],
]:
    """
    Синтетический набор данных для проверки форматирования без ffprobe/ФС.
    Данные находятся в synthetic_dataset.py.
    """
    from synthetic_dataset import load_synthetic_cases, make_track_paths

    per_dir_seconds: dict[Path, float] = {}
    per_dir_count: dict[Path, int] = {}
    per_dir_sr: dict[Path, set[int]] = {}
    per_dir_bit: dict[Path, set[int]] = {}
    per_dir_exts: dict[Path, set[str]] = {}
    per_dir_files: dict[Path, list[Path]] = {}
    per_dir_dr: dict[Path, str | None] = {}

    total_seconds = 0.0
    total_tracks = 0
    total_sr: set[int] = set()
    total_bit: set[int] = set()
    total_exts: set[str] = set()
    all_years: list[int] = []

    for case in load_synthetic_cases():
        g = case["group"]
        folder_name = case["folder_name"]
        secs = float(case["seconds"])
        sr = int(case["sample_rate"])
        bit = int(case["bit_depth"])
        ext = str(case["ext"])
        track_titles = list(case["track_titles"])
        dr_text = str(case["dr_text"])

        folder = root / g / folder_name
        audio_files = make_track_paths(folder, ext, track_titles)

        per_dir_seconds[folder] = secs
        per_dir_count[folder] = len(audio_files)
        per_dir_sr[folder] = {sr}
        per_dir_bit[folder] = {bit}
        per_dir_exts[folder] = {ext}
        per_dir_files[folder] = audio_files
        per_dir_dr[folder] = dr_text

        total_seconds += secs
        total_tracks += len(audio_files)
        total_sr.add(sr)
        total_bit.add(bit)
        total_exts.add(ext)

        rel = folder.relative_to(root)
        all_years.extend(extract_years_from_text(rel.as_posix()))

    return (
        per_dir_seconds,
        per_dir_count,
        per_dir_sr,
        per_dir_bit,
        per_dir_exts,
        per_dir_files,
        per_dir_dr,
        total_seconds,
        total_tracks,
        total_sr,
        total_bit,
        total_exts,
        all_years,
    )

# ----------------------------
# CLI / main
# ----------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Sum durations grouped per release folder; show bit depth + sample rate; optionally generate BBCode release template."
    )
    ap.add_argument("path", nargs="?", default=".", help="Root folder (default: current directory).")
    ap.add_argument("--ext", action="append", default=[], help="Add extension (e.g. --ext .flac). Repeatable.")
    ap.add_argument("--include-root", action="store_true", help="Include tracks directly inside the root folder.")
    ap.add_argument("--flat", action="store_true", help="Flat output without group headers (Albums/Singles).")
    ap.add_argument("--release", action="store_true", help="Write BBCode release template to /tmp/<root_folder_name>.")
    ap.add_argument("--dr", default=None, help="Directory with DR reports (e.g. *_dr.txt). Use with --release.")
    ap.add_argument("--test", action="store_true", help="Generate fake data (no ffprobe/files needed) to test output formatting.")
    ap.add_argument("--normalize", action="store_true", help="Normalize release folder names (dry run by default).")
    ap.add_argument("--y", action="store_true", help="Apply rename changes for --normalize.")
    return ap

def normalize_exts(user_exts: list[str]) -> set[str]:
    """Объединяем дефолтные расширения и пользовательские --ext."""
    exts = set(AUDIO_EXTS_DEFAULT)
    for e in user_exts:
        e = e.strip().lower()
        if e and not e.startswith("."):
            e = "." + e
        if e:
            exts.add(e)
    return exts

def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    root = Path(args.path).expanduser().resolve()

    # В режиме --test мы НЕ трогаем файловую систему и не требуем ffprobe
    if not args.test:
        if not root.exists() or not root.is_dir():
            print(f"Error: '{root}' is not a directory.", file=sys.stderr)
            return 2

    if args.normalize:
        if args.test:
            print("Error: --normalize can't be used with --test.", file=sys.stderr)
            return 2
        if which("ffprobe") is None:
            print("Error: ffprobe not found. Install ffmpeg (ffprobe) and retry.", file=sys.stderr)
            return 3
        exts = normalize_exts(args.ext)
        normalize_release_folders(root, exts, apply=args.y)
        return 0

    if args.y:
        print("Warning: --y has effect only with --normalize.", file=sys.stderr)

    if not args.test:
        if which("ffprobe") is None:
            print("Error: ffprobe not found. Install ffmpeg (ffprobe) and retry.", file=sys.stderr)
            return 3

    exts = normalize_exts(args.ext)

    # Подготовка DR
    dr_dir: Path | None = None
    dr_index: dict[str, Path] = {}
    if args.dr is not None:
        dr_dir = Path(args.dr).expanduser().resolve()
        if not dr_dir.exists() or not dr_dir.is_dir():
            print(f"Warning: --dr path is not a directory: {dr_dir}", file=sys.stderr)
            dr_dir = None
        else:
            dr_index = build_dr_index(dr_dir)

    # ---------- сбор статистики ----------
    per_dir_dr: dict[Path, str | None] = {}

    if args.test:
        (
            per_dir_seconds,
            per_dir_count,
            per_dir_sr,
            per_dir_bit,
            per_dir_exts,
            per_dir_files,
            per_dir_dr,
            total_seconds,
            total_tracks,
            total_sr,
            total_bit,
            total_exts,
            all_years,
        ) = collect_synthetic_stats(root)
    else:
        (
            per_dir_seconds,
            per_dir_count,
            per_dir_sr,
            per_dir_bit,
            per_dir_exts,
            per_dir_files,
            total_seconds,
            total_tracks,
            total_sr,
            total_bit,
            total_exts,
            all_years,
        ) = collect_real_stats(root, exts, args.include_root)

    if not per_dir_seconds:
        print("No audio files found.")
        return 0

    total_releases = len(per_dir_seconds)

    # ---------- подготовка элементов для консольного вывода ----------
    items: list[tuple[Path, float, int, set[int], set[int]]] = []
    for folder_abs, secs in per_dir_seconds.items():
        rel = folder_abs.relative_to(root)
        cnt = per_dir_count.get(folder_abs, 0)
        srset = per_dir_sr.get(folder_abs, set())
        bitset = per_dir_bit.get(folder_abs, set())
        items.append((rel, secs, cnt, srset, bitset))

    items.sort(key=lambda x: (group_sort_index(group_key(x[0])), x[0].as_posix().lower()))

    # ---------- вывод в консоль ----------
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
        cover_uploader: FastPicCoverUploader | None = None
        if not args.test:
            if requests is None:
                print("Warning: 'requests' not installed; skipping FastPic cover uploads.", file=sys.stderr)
            else:
                cover_uploader = FastPicCoverUploader(resize_to=500)

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
            if args.test:
                dr_text = per_dir_dr.get(folder_abs)
            elif dr_dir is not None:
                dr_text = find_dr_text_for_release(folder_name, dr_dir, dr_index)

            cover_url = None
            if cover_uploader is not None:
                cover_path = find_cover_jpg(folder_abs)
                if cover_path is not None:
                    try:
                        cover_url = cover_uploader.upload(cover_path)
                    except Exception as e:
                        print(f"Warning: cover upload failed for {cover_path}: {e}", file=sys.stderr)

            grouped.setdefault(g, []).append(
                {
                    "title": title,
                    "year": year,
                    "duration": format_hhmmss(per_dir_seconds[folder_abs]),
                    "tracklist": tracklist,
                    "dr": dr_text,
                    "cover_url": cover_url,
                }
            )

        # Сортировка релизов внутри группы: по году, затем по названию
        for g, lst in grouped.items():
            lst.sort(key=lambda r: ((r["year"] or 9999), str(r["title"]).lower()))

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
                overall_codec=codec_label(total_exts),
                release=single_release,
            )
        else:
            bbcode = make_release_bbcode(
                root_name=root.name,
                year_range=year_range,
                total_duration=format_hhmmss(total_seconds),
                overall_codec=codec_label(total_exts),
                overall_bit=bit_label(total_bit),
                overall_sr=sr_label(total_sr),
                grouped_releases=grouped,
            )

        out_path = Path.cwd() / f"{root.name}.txt"
        out_path.write_text(bbcode, encoding="utf-8")
        print(f"\nWrote release template: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
