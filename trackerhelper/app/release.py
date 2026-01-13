from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path

from ..domain.grouping import ReleaseBBCodeItem, group_bbcode_releases
from ..domain.models import ReleaseBBCode
from ..domain.utils import (
    bit_label,
    codec_label,
    format_hhmmss,
    group_key,
    parse_release_title_and_year,
    sr_label,
)
from ..formatting.bbcode import make_release_bbcode, make_single_release_bbcode
from ..formatting.tracklist import build_tracklist_lines
from ..infra.cover import FastPicCoverUploader, find_cover_jpg, requests as cover_requests
from ..infra.dr import build_dr_index, find_dr_text_for_release
from ..infra.ffprobe import FfprobeClient
from .progress import ProgressCallback
from .stats import collect_stats, collect_synthetic_stats

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReleaseBuildResult:
    bbcode: str
    total_releases: int
    missing_covers: list[Path]
    missing_drs: list[Path]
    dr_checked: bool


def _normalize_lang(lang: str | None) -> str:
    if not lang:
        return "ru"
    lang_norm = lang.lower()
    return "en" if lang_norm == "en" else "ru"


def build_release_bbcode(
    root: Path,
    exts: set[str],
    include_root: bool,
    *,
    dr_dir: Path | None,
    test_mode: bool,
    no_cover: bool,
    lang: str,
    progress: ProgressCallback | None = None,
) -> ReleaseBuildResult | None:
    if test_mode:
        releases, summary = collect_synthetic_stats(root)
    else:
        ffprobe = FfprobeClient()
        releases, summary = collect_stats(root, exts, include_root, ffprobe, progress=progress)

    if not releases:
        return None

    dr_index: dict[str, Path] = {}
    if dr_dir is not None:
        dr_index = build_dr_index(dr_dir)
        dr_checked = True
    else:
        dr_checked = False

    cover_uploader: FastPicCoverUploader | None = None
    if not test_mode and not no_cover:
        if cover_requests is None:
            logger.warning("Warning: 'requests' not installed; skipping FastPic cover uploads.")
        else:
            cover_uploader = FastPicCoverUploader(resize_to=500)

    year_range = None
    if summary.all_years:
        y_min, y_max = min(summary.all_years), max(summary.all_years)
        year_range = f"{y_min}-{y_max}" if y_min != y_max else f"{y_min}"

    items: list[ReleaseBBCodeItem] = []
    missing_covers: list[Path] = []
    missing_drs: list[Path] = []
    for rel in releases:
        rel_path = rel.path.relative_to(root)
        group = group_key(rel_path)

        folder_name = rel.path.name
        title, year = parse_release_title_and_year(folder_name)
        tracklist = build_tracklist_lines(rel.audio_files, sort=False)

        dr_text = None
        if test_mode:
            dr_text = rel.dr_text
        elif dr_dir is not None:
            dr_text = find_dr_text_for_release(folder_name, dr_dir, dr_index)
        if dr_checked and dr_text is None:
            missing_drs.append(rel.path)

        cover_url = None
        cover_path = find_cover_jpg(rel.path)
        if cover_path is None:
            missing_covers.append(rel.path)
        elif cover_uploader is not None:
            try:
                cover_url = cover_uploader.upload(cover_path)
            except Exception as exc:
                logger.warning("Warning: cover upload failed for %s: %s", cover_path, exc)

        items.append(
            ReleaseBBCodeItem(
                group=group,
                release=ReleaseBBCode(
                    title=title,
                    year=year,
                    duration=format_hhmmss(rel.duration_seconds),
                    tracklist=tracklist,
                    dr=dr_text,
                    cover_url=cover_url,
                ),
            )
        )

    total_releases = len(releases)
    lang = _normalize_lang(lang)
    groups = group_bbcode_releases(items)

    if total_releases == 1:
        single_release = groups[0].releases[0] if groups and groups[0].releases else None
        if single_release is None:
            logger.warning("Warning: no releases found for BBCode generation.")
            return None

        bbcode = make_single_release_bbcode(
            root_name=root.name,
            year_range=year_range,
            overall_codec=codec_label(summary.total_exts),
            release=single_release,
            lang=lang,
        )
    else:
        bbcode = make_release_bbcode(
            root_name=root.name,
            year_range=year_range,
            total_duration=format_hhmmss(summary.total_seconds),
            overall_codec=codec_label(summary.total_exts),
            overall_bit=bit_label(summary.total_bit),
            overall_sr=sr_label(summary.total_sr),
            grouped_releases=groups,
            lang=lang,
        )

    return ReleaseBuildResult(
        bbcode=bbcode,
        total_releases=total_releases,
        missing_covers=missing_covers,
        missing_drs=missing_drs,
        dr_checked=dr_checked,
    )
