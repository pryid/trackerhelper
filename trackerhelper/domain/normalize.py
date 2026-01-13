from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .utils import clean_name_part


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
