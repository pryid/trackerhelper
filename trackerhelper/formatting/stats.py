from __future__ import annotations

import json
from typing import Any
from pathlib import Path

from ..domain.grouping import ReleaseGroup
from ..domain.models import Release, StatsSummary
from ..domain.utils import (
    bit_label,
    format_hhmmss,
    group_key,
    release_word,
    sr_label,
    track_word,
)


def _format_release_path(root: Path, release_path: Path) -> str:
    rel_path = release_path.relative_to(root)
    return Path(*rel_path.parts[1:]).as_posix() if len(rel_path.parts) > 1 else rel_path.as_posix()


def _format_track_duration(duration: float | None) -> str:
    return format_hhmmss(duration) if duration is not None else "unknown"


def render_stats_text(
    groups: list[ReleaseGroup],
    summary: StatsSummary,
    root: Path,
    *,
    include_tracks: bool = False,
) -> str:
    lines: list[str] = []

    for i, group in enumerate(groups):
        if i:
            lines.append("")
        lines.append(f"{group.name}:")
        for rel in group.releases:
            pretty = _format_release_path(root, rel.path)
            lines.append(
                f"  {pretty} - {format_hhmmss(rel.duration_seconds)} "
                f"({rel.track_count} {track_word(rel.track_count)}, "
                f"{bit_label(rel.bit_depths)}, {sr_label(rel.sample_rates)})"
            )
            if include_tracks:
                for track in rel.tracks:
                    dur = _format_track_duration(track.duration_seconds)
                    sr = f"{track.sample_rate} Hz" if track.sample_rate is not None else "unknown"
                    bit = f"{track.bit_depth}-bit" if track.bit_depth is not None else "unknown"
                    lines.append(f"    {track.path.name} - {dur} ({sr}, {bit})")

    total_releases = sum(len(group.releases) for group in groups)
    lines.append(
        f"\nTotal: {format_hhmmss(summary.total_seconds)} "
        f"({summary.total_tracks} {track_word(summary.total_tracks)}, "
        f"{total_releases} {release_word(total_releases)})"
    )

    return "\n".join(lines)


def render_stats_json(
    groups: list[ReleaseGroup],
    summary: StatsSummary,
    root: Path,
    *,
    include_tracks: bool = False,
) -> str:
    groups_list: list[dict[str, Any]] = []
    data: dict[str, Any] = {
        "groups": groups_list,
        "summary": {
            "total_seconds": summary.total_seconds,
            "total_duration": format_hhmmss(summary.total_seconds),
            "total_tracks": summary.total_tracks,
            "total_releases": sum(len(group.releases) for group in groups),
            "sample_rates": sorted(summary.total_sr),
            "bit_depths": sorted(summary.total_bit),
            "exts": sorted(summary.total_exts),
        },
    }

    for group in groups:
        releases_list: list[dict[str, Any]] = []
        group_item: dict[str, Any] = {"name": group.name, "releases": releases_list}
        for rel in group.releases:
            rel_path = rel.path.relative_to(root).as_posix()
            releases_list.append(
                {
                    "rel_path": rel_path,
                    "display_path": _format_release_path(root, rel.path),
                    "duration_seconds": rel.duration_seconds,
                    "duration": format_hhmmss(rel.duration_seconds),
                    "track_count": rel.track_count,
                    "sample_rates": sorted(rel.sample_rates),
                    "bit_depths": sorted(rel.bit_depths),
                    "exts": sorted(rel.exts),
                }
            )
            if include_tracks:
                track_items: list[dict[str, Any]] = []
                for track in rel.tracks:
                    duration = track.duration_seconds
                    track_items.append(
                        {
                            "rel_path": track.path.relative_to(root).as_posix(),
                            "file_name": track.path.name,
                            "duration_seconds": duration,
                            "duration": _format_track_duration(duration) if duration is not None else None,
                            "sample_rate": track.sample_rate,
                            "bit_depth": track.bit_depth,
                            "ext": track.ext,
                        }
                    )
                releases_list[-1]["tracks"] = track_items
        groups_list.append(group_item)

    return json.dumps(data, ensure_ascii=False)


def render_stats_csv(releases: list[Release], root: Path) -> str:
    lines = ["group,rel_path,display_path,duration_seconds,duration,track_count,sample_rates,bit_depths,exts"]
    for rel in releases:
        rel_path = rel.path.relative_to(root).as_posix()
        group = group_key(rel.path.relative_to(root))
        sample_rates = ";".join(str(v) for v in sorted(rel.sample_rates))
        bit_depths = ";".join(str(v) for v in sorted(rel.bit_depths))
        exts = ";".join(sorted(rel.exts))
        lines.append(
            "{group},{rel_path},{display},{seconds},{duration},{tracks},{sr},{bit},{exts}".format(
                group=group,
                rel_path=rel_path,
                display=_format_release_path(root, rel.path),
                seconds=rel.duration_seconds,
                duration=format_hhmmss(rel.duration_seconds),
                tracks=rel.track_count,
                sr=sample_rates,
                bit=bit_depths,
                exts=exts,
            )
        )
    return "\n".join(lines)


def render_stats_csv_tracks(releases: list[Release], root: Path) -> str:
    lines = [
        "group,rel_path,display_path,track_rel_path,track_name,track_ext,"
        "duration_seconds,duration,sample_rate,bit_depth"
    ]
    for rel in releases:
        rel_path = rel.path.relative_to(root).as_posix()
        group = group_key(rel.path.relative_to(root))
        display = _format_release_path(root, rel.path)
        for track in rel.tracks:
            track_rel = track.path.relative_to(root).as_posix()
            duration = track.duration_seconds
            duration_text = _format_track_duration(duration) if duration is not None else ""
            lines.append(
                "{group},{rel_path},{display},{track_rel},{track_name},{track_ext},{seconds},{duration},"
                "{sr},{bit}".format(
                    group=group,
                    rel_path=rel_path,
                    display=display,
                    track_rel=track_rel,
                    track_name=track.path.name,
                    track_ext=track.ext,
                    seconds="" if duration is None else duration,
                    duration=duration_text,
                    sr="" if track.sample_rate is None else track.sample_rate,
                    bit="" if track.bit_depth is None else track.bit_depth,
                )
            )
    return "\n".join(lines)
