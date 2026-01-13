from __future__ import annotations

import re
from pathlib import Path

from .constants import PREFERRED_GROUP_ORDER


def clean_name_part(s: str) -> str:
    """Normalize whitespace and dashes for folder naming."""
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def format_hhmmss(total_seconds: float) -> str:
    """Format seconds as HH:MM:SS."""
    s = int(round(total_seconds))
    h = s // 3600
    s %= 3600
    m = s // 60
    s %= 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_khz(sr_hz: int) -> str:
    """Sample rate in kHz (same behavior as before)."""
    if sr_hz % 1000 == 0:
        return f"{sr_hz // 1000}"
    return f"{sr_hz / 1000:.1f}".rstrip("0").rstrip(".")


def track_word(n: int) -> str:
    """Return a singular/plural label for track count."""
    return "track" if n == 1 else "tracks"


def release_word(n: int) -> str:
    """Return a singular/plural label for release count."""
    return "release" if n == 1 else "releases"


def sr_label(srset: set[int]) -> str:
    """Return a sample rate label for output."""
    if len(srset) == 1:
        return f"{format_khz(next(iter(srset)))} khz"
    if len(srset) > 1:
        return "mixed khz"
    return "unknown khz"


def bit_label(bitset: set[int]) -> str:
    """Return a bit depth label for output."""
    if len(bitset) == 1:
        return f"{next(iter(bitset))} bit"
    if len(bitset) > 1:
        return "mixed bit"
    return "unknown bit"


def codec_label(exts: set[str]) -> str:
    """Return a codec label based on extensions."""
    if len(exts) == 1:
        e = next(iter(exts))
        return f"{e.lstrip('.').upper()} (*{e})"
    if len(exts) > 1:
        joined = "/".join(f"*{e}" for e in sorted(exts))
        return f"mixed ({joined})"
    return "unknown"


# ----------------------------
# Release grouping and sorting
# ----------------------------

def group_key(rel_folder: Path) -> str:
    """Group equals the first segment of the relative path (Albums/Singles/etc.)."""
    parts = rel_folder.parts
    return parts[0] if parts else "."


def group_sort_index(g: str) -> tuple[int, str]:
    """Sort groups: preferred order first, then alphabetically."""
    if g in PREFERRED_GROUP_ORDER:
        return (PREFERRED_GROUP_ORDER.index(g), "")
    return (len(PREFERRED_GROUP_ORDER), g.lower())


def parse_release_title_and_year(folder_name: str) -> tuple[str, int | None]:
    """
    Try to parse \"Title - 2020\" or \"Title - 2020\" (dash variants).
    Returns (title, year|None).
    """
    m = re.match(r"^(.*?)(?:\s*[-\u2013]\s*)(\d{4})\s*$", folder_name)
    if not m:
        m = re.match(r"^(\d{4})(?:\s*[-\u2013]\s*)(.*)$", folder_name)
        if not m:
            return folder_name, None
        try:
            year = int(m.group(1))
        except ValueError:
            year = None
        title = m.group(2).strip()
        return (title if title else folder_name, year)
    title = m.group(1).strip()
    try:
        year = int(m.group(2))
    except ValueError:
        year = None
    return (title if title else folder_name, year)


def extract_years_from_text(s: str) -> list[int]:
    """Find years in any text (used for year_range based on folder structure)."""
    return [int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", s)]


def parse_year_from_text(s: str) -> int | None:
    """Extract the last 4-digit year from text."""
    years = extract_years_from_text(s)
    return years[-1] if years else None
