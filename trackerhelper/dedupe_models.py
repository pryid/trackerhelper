from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set


@dataclass(frozen=True)
class TrackFingerprint:
    duration: str
    fingerprint: str


@dataclass(frozen=True)
class FingerprintRow:
    duration: str
    fingerprint: str
    path: str


@dataclass
class DedupeResult:
    redundant: Set[str]
    duplicate_of: Dict[str, str]
    contained_in: Dict[str, str]
    unique_count: Dict[str, int]
    sizes: Dict[str, int]
    post_contained: List["ReleaseContainment"]
    unsafe: List[str]


@dataclass(frozen=True)
class ReleaseContainment:
    subset: str
    superset: str
