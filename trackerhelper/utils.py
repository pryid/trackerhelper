from __future__ import annotations

import re
import shutil
from pathlib import Path

from .constants import PREFERRED_GROUP_ORDER


def which(cmd: str) -> str | None:
    """Возвращает путь к исполняемому файлу в PATH или None."""
    return shutil.which(cmd)


def clean_name_part(s: str) -> str:
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


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
