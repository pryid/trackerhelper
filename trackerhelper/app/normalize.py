from __future__ import annotations

import logging
from pathlib import Path

from ..domain.normalize import (
    NormalizationInput,
    NormalizationPlan,
    NormalizationSkip,
    build_normalization_plan,
    parse_year_from_folder_name,
)
from ..domain.tags import select_release_metadata
from ..infra.ffprobe import FfprobeClient, TagsReader
from ..infra.scan import ReleaseScan, iter_release_scans
from .progress import ProgressCallback

logger = logging.getLogger(__name__)


def _release_scan_sort_key(item: ReleaseScan) -> str:
    return item.path.as_posix().lower()


def plan_normalization(
    root: Path,
    exts: set[str],
    tag_reader: TagsReader | None = None,
    progress: ProgressCallback | None = None,
) -> NormalizationPlan:
    """Build a normalization plan and skip unsafe targets."""
    ffprobe = tag_reader or FfprobeClient()
    release_data = list(iter_release_scans(root, exts, include_root=True))
    release_data.sort(key=_release_scan_sort_key)

    if not release_data:
        return NormalizationPlan(actions=[], skipped=[])

    single_mode = len(release_data) == 1
    if not single_mode:
        release_data = [item for item in release_data if item.path != root]
        if not release_data:
            single_mode = True
            release_data = [ReleaseScan(path=root, audio_files=[])]

    total_files = sum(len(item.audio_files) for item in release_data)
    if progress is not None:
        progress.start(total_files)

    inputs: list[NormalizationInput] = []
    for item in release_data:
        tags_list: list[dict[str, str]] = []
        for path in item.audio_files:
            tags_list.append(ffprobe.get_tags(path))
            if progress is not None:
                progress.advance()
        artist, album = select_release_metadata(tags_list)
        year = parse_year_from_folder_name(item.path.name)
        inputs.append(NormalizationInput(path=item.path, artist=artist, album=album, year=year))

    plan = build_normalization_plan(inputs, single_mode=single_mode)
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
