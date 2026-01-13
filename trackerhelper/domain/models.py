from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Track:
    path: Path
    duration_seconds: float | None = None
    sample_rate: int | None = None
    bit_depth: int | None = None

    @property
    def ext(self) -> str:
        return self.path.suffix.lower()


@dataclass
class Release:
    path: Path
    duration_seconds: float
    track_count: int
    sample_rates: set[int] = field(default_factory=set)
    bit_depths: set[int] = field(default_factory=set)
    exts: set[str] = field(default_factory=set)
    tracks: list[Track] = field(default_factory=list)
    dr_text: str | None = None

    @property
    def audio_files(self) -> list[Path]:
        return [track.path for track in self.tracks]


@dataclass
class ReleaseGroup:
    name: str
    releases: list[Release] = field(default_factory=list)

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


@dataclass
class ReleaseGroupBBCode:
    name: str
    releases: list[ReleaseBBCode] = field(default_factory=list)
