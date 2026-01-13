from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Set


@dataclass(frozen=True)
class TrackFingerprint:
    duration: str
    fingerprint: str


@dataclass(frozen=True)
class FingerprintRow:
    duration: str
    fingerprint: str
    path: Path


@dataclass
class DedupeResult:
    redundant: Set[Path]
    duplicate_of: Dict[Path, Path]
    contained_in: Dict[Path, Path]
    unique_count: Dict[Path, int]
    sizes: Dict[Path, int]
    post_contained: List["ReleaseContainment"]
    unsafe: List[Path]


@dataclass(frozen=True)
class ReleaseContainment:
    subset: Path
    superset: Path


def score_release(rel: Path) -> int:
    """Heuristic for "keep the best" when content is identical."""
    parts = [part.lower() for part in rel.parts]
    s = rel.as_posix().lower()
    score = 0
    if "albums" in parts:
        score += 100
    if "deluxe" in s:
        score += 6
    if "edition" in s:
        score += 4
    if "reimagined" in s:
        score += 2
    if "sampler" in s:
        score -= 3
    return score


def canon_release_sort_key(rel: Path) -> tuple[int, int, str]:
    """Sort key for picking the canonical release."""
    return (-score_release(rel), len(rel.as_posix()), rel.as_posix())


def build_release_keys(
    rows: list[FingerprintRow],
    release_resolver: Callable[[Path], Path | None],
) -> Dict[Path, Set[TrackFingerprint]]:
    """Build a release -> fingerprints mapping."""
    release_keys: Dict[Path, Set[TrackFingerprint]] = {}
    for row in rows:
        rel = release_resolver(row.path)
        if not rel:
            continue
        release_keys.setdefault(rel, set()).add(TrackFingerprint(row.duration, row.fingerprint))
    return release_keys


def find_redundant_releases(release_keys: Dict[Path, Set[TrackFingerprint]]) -> DedupeResult:
    """Find redundant releases using exact-match and subset rules."""
    releases = sorted(release_keys.keys(), key=lambda r: r.as_posix())
    sizes = {r: len(release_keys[r]) for r in releases}

    track_to_releases: Dict[TrackFingerprint, Set[Path]] = {}
    for r in releases:
        for k in release_keys[r]:
            track_to_releases.setdefault(k, set()).add(r)

    unique_count = {
        r: sum(1 for k in release_keys[r] if len(track_to_releases[k]) == 1)
        for r in releases
    }

    by_set: Dict[frozenset, List[Path]] = {}
    for r in releases:
        ks = release_keys[r]
        if ks:
            by_set.setdefault(frozenset(ks), []).append(r)

    duplicate_of: Dict[Path, Path] = {}
    canon_of_set: Dict[frozenset, Path] = {}

    for aset, group in by_set.items():
        if len(group) <= 1:
            continue
        canon = sorted(group, key=canon_release_sort_key)[0]
        canon_of_set[aset] = canon
        for g in group:
            if g != canon:
                duplicate_of[g] = canon

    contained_in: Dict[Path, Path] = {}
    for a in releases:
        if a in duplicate_of:
            continue
        A = release_keys[a]
        if not A:
            continue

        def track_rarity_key(track_key: TrackFingerprint) -> int:
            return len(track_to_releases[track_key])

        rare_track = min(A, key=track_rarity_key)
        candidates = track_to_releases[rare_track] - {a}
        best: Path | None = None
        for b in candidates:
            B = release_keys[b]
            if len(B) < len(A):
                continue
            if A.issubset(B):
                if best is None:
                    best = b
                else:
                    if (sizes[b], -score_release(b), b.as_posix()) < (
                        sizes[best],
                        -score_release(best),
                        best.as_posix(),
                    ):
                        best = b
        if best is not None and best != a:
            contained_in[a] = best

    redundant: Set[Path] = set(duplicate_of.keys())
    canons: Set[Path] = set(canon_of_set.values())

    for a, b in contained_in.items():
        if a not in canons:
            redundant.add(a)

    unsafe = sorted([r for r in redundant if unique_count.get(r, 0) > 0], key=lambda r: r.as_posix())
    if unsafe:
        for r in unsafe:
            redundant.discard(r)

    remaining = [r for r in releases if r not in redundant and release_keys[r]]
    post_contained: List[ReleaseContainment] = []
    for a in remaining:
        A = release_keys[a]
        for b in remaining:
            if b == a:
                continue
            B = release_keys[b]
            if A != B and A.issubset(B):
                post_contained.append(ReleaseContainment(subset=a, superset=b))
                break

    return DedupeResult(
        redundant=redundant,
        duplicate_of=duplicate_of,
        contained_in=contained_in,
        unique_count=unique_count,
        sizes=sizes,
        post_contained=post_contained,
        unsafe=unsafe,
    )
