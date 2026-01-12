from __future__ import annotations

import re
from pathlib import Path


def normalize_name(s: str) -> str:
    """Normalize names to match release titles with DR files."""
    s = s.strip().lower()
    s = s.replace("\u0451", "\u0435")
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    s = re.sub(r"\s+", " ", s)
    return s


def strip_dr_suffix(stem: str) -> str:
    """Remove suffixes like _dr, -dr, (dr) from the filename (without extension)."""
    s = stem
    s = re.sub(r"[\s._-]*(dr|d\.r\.)\s*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*\(dr\)\s*$", "", s, flags=re.IGNORECASE)
    return s.strip()


def read_text_guess(path: Path) -> str:
    """
    Try to read text using common encodings.
    Useful for DR reports that are sometimes cp1251.
    """
    try:
        data = path.read_bytes()
    except Exception:
        return path.read_text(encoding="utf-8", errors="replace")

    for enc in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def build_dr_index(dr_dir: Path) -> dict[str, Path]:
    """
    Index: normalized_release_name -> path to txt.
    Used as a fallback when there is no exact filename match.
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
    Find a DR report for a release folder.

    First try exact patterns, then fall back to the normalize_name index.
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
