from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

from .dedupe_models import DedupeResult, FingerprintRow, ReleaseContainment, TrackFingerprint
from .dedupe_scan import release_dir_from_path


def score_release(rel: str) -> int:
    """
    Heuristic for "keep the best" when content is identical.
    """
    rel_path = Path(rel)
    parts = [part.lower() for part in rel_path.parts]
    s = rel.lower()
    sc = 0
    if "albums" in parts:
        sc += 100
    if "deluxe" in s:
        sc += 6
    if "edition" in s:
        sc += 4
    if "reimagined" in s:
        sc += 2
    if "sampler" in s:
        sc -= 3
    return sc


def canon_release_sort_key(rel: str) -> tuple[int, int, str]:
    """Sort key for picking the canonical release."""
    return (-score_release(rel), len(rel), rel)


def build_release_keys(rows: list[FingerprintRow]) -> Dict[str, Set[TrackFingerprint]]:
    """Build a release -> fingerprints mapping."""
    release_keys: Dict[str, Set[TrackFingerprint]] = defaultdict(set)
    for row in rows:
        rel = release_dir_from_path(Path(row.path))
        if not rel:
            continue
        release_keys[rel].add(TrackFingerprint(row.duration, row.fingerprint))
    return release_keys


def find_redundant_releases(release_keys: Dict[str, Set[TrackFingerprint]]) -> DedupeResult:
    """Find redundant releases using exact-match and subset rules."""
    releases = sorted(release_keys.keys())
    sizes = {r: len(release_keys[r]) for r in releases}

    track_to_releases: Dict[TrackFingerprint, Set[str]] = defaultdict(set)
    for r in releases:
        for k in release_keys[r]:
            track_to_releases[k].add(r)

    unique_count = {
        r: sum(1 for k in release_keys[r] if len(track_to_releases[k]) == 1)
        for r in releases
    }

    by_set: Dict[frozenset, List[str]] = defaultdict(list)
    for r in releases:
        ks = release_keys[r]
        if ks:
            by_set[frozenset(ks)].append(r)

    duplicate_of: Dict[str, str] = {}
    canon_of_set: Dict[frozenset, str] = {}

    for aset, group in by_set.items():
        if len(group) <= 1:
            continue
        canon = sorted(group, key=canon_release_sort_key)[0]
        canon_of_set[aset] = canon
        for g in group:
            if g != canon:
                duplicate_of[g] = canon

    contained_in: Dict[str, str] = {}
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
        best = None
        for b in candidates:
            B = release_keys[b]
            if len(B) < len(A):
                continue
            if A.issubset(B):
                if best is None:
                    best = b
                else:
                    if (sizes[b], -score_release(b), b) < (sizes[best], -score_release(best), best):
                        best = b
        if best is not None and best != a:
            contained_in[a] = best

    redundant: Set[str] = set(duplicate_of.keys())
    canons: Set[str] = set(canon_of_set.values())

    for a, b in contained_in.items():
        if a not in canons:
            redundant.add(a)

    unsafe = sorted([r for r in redundant if unique_count.get(r, 0) > 0])
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
