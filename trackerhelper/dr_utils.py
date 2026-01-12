from __future__ import annotations

import re
from pathlib import Path


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
