from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..domain.dedupe import DedupeResult

PLAN_VERSION = 1


def _path_map(values: dict) -> dict[str, str]:
    return {k.as_posix(): v.as_posix() for k, v in values.items()}


def _count_map(values: dict) -> dict[str, int]:
    return {k.as_posix(): v for k, v in values.items()}


def dedupe_result_to_dict(
    result: DedupeResult,
    *,
    roots: list | None = None,
    exts: set | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "version": PLAN_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "redundant": sorted([p.as_posix() for p in result.redundant]),
        "duplicate_of": _path_map(result.duplicate_of),
        "contained_in": _path_map(result.contained_in),
        "unsafe": sorted([p.as_posix() for p in result.unsafe]),
        "sizes": _count_map(result.sizes),
        "unique_count": _count_map(result.unique_count),
        "post_contained": [
            {"subset": rel.subset.as_posix(), "superset": rel.superset.as_posix()}
            for rel in result.post_contained
        ],
    }
    if roots is not None:
        payload["roots"] = [p.as_posix() for p in roots]
    if exts is not None:
        payload["exts"] = sorted(exts)
    return payload


def render_dedupe_csv(result: DedupeResult) -> str:
    lines = ["release,action,reason,reference,tracks,unique_tracks"]
    for rel in sorted(result.redundant, key=lambda p: p.as_posix()):
        reason = "duplicate" if rel in result.duplicate_of else "contained"
        reference = result.duplicate_of.get(rel) or result.contained_in.get(rel)
        reference_str = reference.as_posix() if reference is not None else ""
        tracks = result.sizes.get(rel)
        unique = result.unique_count.get(rel)
        lines.append(
            "{release},{action},{reason},{reference},{tracks},{unique}".format(
                release=rel.as_posix(),
                action="remove",
                reason=reason,
                reference=reference_str,
                tracks=tracks if tracks is not None else "",
                unique=unique if unique is not None else "",
            )
        )
    return "\n".join(lines)
