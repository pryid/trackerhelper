from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import Release, ReleaseBBCode, ReleaseGroup, ReleaseGroupBBCode
from .utils import group_key, group_sort_index


@dataclass(frozen=True)
class ReleaseBBCodeItem:
    group: str
    release: ReleaseBBCode


def release_path_sort_key(rel_path: Path) -> tuple[tuple[int, str], str]:
    """Sort key that keeps preferred groups first, then path name."""
    return (group_sort_index(group_key(rel_path)), rel_path.as_posix().lower())


def group_releases(releases: list[Release], root: Path) -> list[ReleaseGroup]:
    """Group releases by top-level folder in a stable sort order."""
    grouped: list[ReleaseGroup] = []
    sorted_releases = sorted(
        releases,
        key=lambda rel: release_path_sort_key(rel.path.relative_to(root)),
    )

    for rel in sorted_releases:
        group_name = group_key(rel.path.relative_to(root))
        if not grouped or grouped[-1].name != group_name:
            grouped.append(ReleaseGroup(name=group_name))
        grouped[-1].releases.append(rel)

    return grouped


def group_bbcode_releases(items: list[ReleaseBBCodeItem]) -> list[ReleaseGroupBBCode]:
    """Group BBCode releases by name and sort them for output."""
    grouped: dict[str, ReleaseGroupBBCode] = {}
    for item in items:
        group = grouped.setdefault(item.group, ReleaseGroupBBCode(name=item.group))
        group.releases.append(item.release)

    groups = sorted(grouped.values(), key=lambda g: group_sort_index(g.name))
    for group in groups:
        group.releases.sort(key=lambda rel: (rel.year or 9999, str(rel.title).lower()))
    return groups
