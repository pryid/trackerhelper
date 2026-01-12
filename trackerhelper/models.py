from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ReleaseStats:
    path: Path
    duration_seconds: float
    track_count: int
    sample_rates: set[int] = field(default_factory=set)
    bit_depths: set[int] = field(default_factory=set)
    exts: set[str] = field(default_factory=set)
    audio_files: list[Path] = field(default_factory=list)
    dr_text: str | None = None


@dataclass
class StatsSummary:
    total_seconds: float
    total_tracks: int
    total_sr: set[int] = field(default_factory=set)
    total_bit: set[int] = field(default_factory=set)
    total_exts: set[str] = field(default_factory=set)
    all_years: list[int] = field(default_factory=list)


@dataclass
class ReleaseBBCode:
    title: str
    year: int | None
    duration: str
    tracklist: list[str]
    dr: str | None
    cover_url: str | None = None
