from __future__ import annotations

from dataclasses import dataclass, field
import re
from pathlib import Path

from .utils import clean_name_part

_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")


@dataclass(frozen=True)
class NormalizationInput:
    path: Path
    artist: str | None
    album: str | None
    year: int | None


@dataclass(frozen=True)
class NormalizationAction:
    source: Path
    target: Path


@dataclass(frozen=True)
class NormalizationSkip:
    path: Path
    reason: str


@dataclass(frozen=True)
class NormalizationPlan:
    actions: list[NormalizationAction] = field(default_factory=list)
    skipped: list[NormalizationSkip] = field(default_factory=list)


def parse_year_from_folder_name(name: str) -> int | None:
    """Extract the last 4-digit year from a folder name."""
    years = [int(m.group(1)) for m in _YEAR_RE.finditer(name)]
    return years[-1] if years else None


def build_normalized_name(
    artist: str | None,
    album: str | None,
    year: int | None,
    single_mode: bool,
) -> str | None:
    """Build the normalized release folder name or return None if data is missing."""
    if not artist or not album or year is None:
        return None
    if single_mode:
        return clean_name_part(f"{artist} - {album} ({year})")
    return clean_name_part(f"{year} - {artist} - {album}")


def build_normalization_plan(
    releases: list[NormalizationInput],
    *,
    single_mode: bool,
) -> NormalizationPlan:
    """Build a normalization plan without touching the filesystem."""
    actions: list[NormalizationAction] = []
    skipped: list[NormalizationSkip] = []
    planned_targets: set[Path] = set()

    for item in releases:
        new_name = build_normalized_name(item.artist, item.album, item.year, single_mode)
        if not new_name:
            skipped.append(NormalizationSkip(path=item.path, reason="missing tags/year"))
            continue

        target = item.path.with_name(new_name)
        if target == item.path:
            skipped.append(NormalizationSkip(path=item.path, reason="already normalized"))
            continue

        if target in planned_targets:
            skipped.append(NormalizationSkip(path=item.path, reason="duplicate target"))
            continue

        planned_targets.add(target)
        actions.append(NormalizationAction(source=item.path, target=target))

    return NormalizationPlan(actions=actions, skipped=skipped)
