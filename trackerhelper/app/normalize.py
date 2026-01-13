from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..domain.normalize import (
    NormalizationInput,
    NormalizationPlan,
    NormalizationSkip,
    build_normalization_plan,
)
from ..domain.tags import append_release_metadata_values, most_common_str, select_release_metadata
from ..domain.utils import parse_year_from_text
from ..infra.ffprobe import FfprobeClient, TagsReader
from ..infra.scan import ReleaseScan
from .progress import ProgressCallback
from .scan import list_release_scans

TAG_SAMPLE_LIMIT = 8
TAG_MIN_SAMPLES = 3
TAG_MAJORITY = 0.6


@dataclass(frozen=True)
class NormalizationInputs:
    inputs: list[NormalizationInput]
    single_mode: bool


def _is_stable(values: list[str]) -> bool:
    if len(values) < TAG_MIN_SAMPLES:
        return False
    top = most_common_str(values)
    if not top:
        return False
    count = sum(1 for v in values if v == top)
    return (count / len(values)) >= TAG_MAJORITY


def _sample_tags(
    audio_files: list[Path],
    ffprobe: TagsReader,
    progress: ProgressCallback | None,
) -> list[dict[str, str]]:
    tags_list: list[dict[str, str]] = []
    album_values: list[str] = []
    album_artist_values: list[str] = []
    artist_values: list[str] = []

    for index, path in enumerate(audio_files):
        if index >= TAG_SAMPLE_LIMIT:
            break
        tags = ffprobe.get_tags(path)
        tags_list.append(tags)
        if progress is not None:
            progress.advance()

        append_release_metadata_values(tags, album_values, album_artist_values, artist_values)

        album_ok = _is_stable(album_values)
        artist_source = album_artist_values if album_artist_values else artist_values
        artist_ok = _is_stable(artist_source)

        if album_ok and artist_ok:
            break

    return tags_list


def _resolve_release_scans(root: Path, exts: set[str]) -> tuple[list[ReleaseScan], bool]:
    release_data = list_release_scans(root, exts, include_root=True, sort=True)
    single_mode = len(release_data) == 1
    if not single_mode:
        release_data = [item for item in release_data if item.path != root]
        if not release_data:
            single_mode = True
            release_data = [ReleaseScan(path=root, audio_files=[])]
    return release_data, single_mode


def collect_normalization_inputs(
    root: Path,
    exts: set[str],
    ffprobe: TagsReader,
    progress: ProgressCallback | None,
) -> NormalizationInputs:
    release_data, single_mode = _resolve_release_scans(root, exts)
    if not release_data:
        return NormalizationInputs(inputs=[], single_mode=single_mode)

    total_files = sum(min(len(item.audio_files), TAG_SAMPLE_LIMIT) for item in release_data)
    if progress is not None:
        progress.start(total_files)

    inputs: list[NormalizationInput] = []
    for item in release_data:
        tags_list = _sample_tags(item.audio_files, ffprobe, progress)
        artist, album = select_release_metadata(tags_list)
        year = parse_year_from_text(item.path.name)
        inputs.append(NormalizationInput(path=item.path, artist=artist, album=album, year=year))

    return NormalizationInputs(inputs=inputs, single_mode=single_mode)


def plan_normalization(
    root: Path,
    exts: set[str],
    tag_reader: TagsReader | None = None,
    progress: ProgressCallback | None = None,
) -> NormalizationPlan:
    """Build a normalization plan and skip unsafe targets."""
    ffprobe = tag_reader or FfprobeClient()
    inputs = collect_normalization_inputs(root, exts, ffprobe, progress)
    if not inputs.inputs:
        if progress is not None:
            progress.finish()
        return NormalizationPlan(actions=[], skipped=[])

    plan = build_normalization_plan(inputs.inputs, single_mode=inputs.single_mode)
    if not plan.actions:
        if progress is not None:
            progress.finish()
        return plan

    actions = []
    skipped = list(plan.skipped)
    for action in plan.actions:
        if action.target.exists() and action.target != action.source:
            skipped.append(
                NormalizationSkip(path=action.source, reason=f"target exists: {action.target}")
            )
            continue
        actions.append(action)

    if progress is not None:
        progress.finish()

    return NormalizationPlan(actions=actions, skipped=skipped)


def apply_normalization(plan: NormalizationPlan) -> int:
    """Apply rename actions from a normalization plan."""
    for action in plan.actions:
        action.source.rename(action.target)
    return len(plan.actions)
