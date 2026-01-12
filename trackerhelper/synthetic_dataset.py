"""
Тестовые (синтетические) данные для режима --test.

Это НЕ unit-тесты, а небольшой набор фикстур, который позволяет:
- проверить форматирование консольного вывода,
- проверить генерацию BBCode,
не имея реальных файлов и ffprobe.

Отдельный файл нужен, чтобы основной скрипт не был "засорён" тестовыми данными.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def make_track_paths(folder: Path, ext: str, titles: list[str]) -> list[Path]:
    """Создаёт список "фейковых" путей к трекам (файлы реально не существуют)."""
    return [folder / f"{i:02d} - {t}{ext}" for i, t in enumerate(titles, 1)]


def load_synthetic_cases() -> list[dict[str, Any]]:
    """
    Возвращает список кейсов. Поля:
    - group: Albums/Singles
    - folder_name: имя папки релиза
    - seconds: длительность релиза (в секундах)
    - sample_rate / bit_depth / ext: метаданные для лейблов
    - track_titles: список треков
    - dr_text: текст DR-отчёта
    """
    return [
        {
            "group": "Albums",
            "folder_name": "Example Album - 2019",
            "seconds": 42 * 60 + 17,
            "sample_rate": 44100,
            "bit_depth": 16,
            "ext": ".flac",
            "track_titles": [
                "Intro", "First Song", "Second Song", "Interlude", "Third Song",
                "Fourth Song", "Fifth Song", "Sixth Song", "Seventh Song", "Outro",
            ],
            "dr_text": (
                "DR log (example)\n\n"
                "DR12 -0.10 dB -13.00 dB 01 Intro\n"
                "DR11 -0.20 dB -12.50 dB 02 First Song\n"
                "...\n"
                "Official DR value: DR12"
            ),
        },
        {
            "group": "Albums",
            "folder_name": "Live EP - 2021",
            "seconds": 23 * 60 + 5,
            "sample_rate": 48000,
            "bit_depth": 24,
            "ext": ".flac",
            "track_titles": ["Live One", "Live Two", "Live Three", "Encore", "Goodbye"],
            "dr_text": (
                "DR log (example)\n\n"
                "DR10 -0.50 dB -12.00 dB 01 Live One\n"
                "...\n"
                "Official DR value: DR10"
            ),
        },
        {
            "group": "Singles",
            "folder_name": "Hit Single - 2020",
            "seconds": 3 * 60 + 45,
            "sample_rate": 44100,
            "bit_depth": 16,
            "ext": ".mp3",
            "track_titles": ["Hit Single"],
            "dr_text": (
                "DR log (example)\n\n"
                "DR8 -1.00 dB -10.00 dB 01 Hit Single\n"
                "Official DR value: DR8"
            ),
        },
        {
            "group": "Singles",
            "folder_name": "Demo Single",
            "seconds": 2 * 60 + 58,
            "sample_rate": 44100,
            "bit_depth": 16,
            "ext": ".flac",
            "track_titles": ["Demo"],
            "dr_text": (
                "DR log (example)\n\n"
                "DR9 -0.80 dB -11.00 dB 01 Demo\n"
                "Official DR value: DR9"
            ),
        },
    ]
