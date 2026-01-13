from __future__ import annotations

from .bbcode_templates import (
    about_section,
    group_close,
    group_open,
    release_header,
    release_item,
    single_dr,
    single_header,
    single_tracklist,
)
from ..domain.constants import (
    BBCODE_LABELS,
    GROUP_TITLES,
    PLACEHOLDER_COVER,
    PLACEHOLDER_DURATION,
    PLACEHOLDER_INFO,
    PLACEHOLDER_TITLE,
    PLACEHOLDER_YEAR,
)
from ..domain.models import ReleaseBBCode, ReleaseGroupBBCode
from ..domain.utils import group_sort_index


def _normalize_lang(lang: str | None) -> str:
    if not lang:
        return "ru"
    lang_norm = lang.lower()
    return lang_norm if lang_norm in BBCODE_LABELS else "ru"


def make_release_bbcode(
    root_name: str,
    year_range: str | None,
    total_duration: str,
    overall_codec: str,
    overall_bit: str,
    overall_sr: str,
    grouped_releases: list[ReleaseGroupBBCode],
    *,
    lang: str = "ru",
) -> str:
    """Render a multi-release BBCode template."""
    lang_key = _normalize_lang(lang)
    labels = BBCODE_LABELS[lang_key]
    group_titles = GROUP_TITLES[lang_key]
    parts: list[str] = []

    parts.append(
        release_header(
            root_name=root_name,
            year_range=year_range,
            overall_codec=overall_codec,
            overall_bit=overall_bit,
            overall_sr=overall_sr,
            total_duration=total_duration,
            labels=labels,
        )
    )

    groups = sorted(grouped_releases, key=lambda g: group_sort_index(g.name))
    for group in groups:
        group_title = group_titles.get(group.name, group.name)
        parts.append(group_open(group_title))

        for rel in group.releases:
            parts.append(release_item(rel, labels))

        parts.append(group_close())

    parts.append(about_section(labels))

    return "".join(parts)


def make_single_release_bbcode(
    root_name: str,
    year_range: str | None,
    overall_codec: str,
    release: ReleaseBBCode,
    *,
    lang: str = "ru",
) -> str:
    """Render a single-release BBCode template."""
    lang_key = _normalize_lang(lang)
    labels = BBCODE_LABELS[lang_key]
    title = str(release.title or "").strip() or PLACEHOLDER_TITLE
    year_val = release.year or year_range or PLACEHOLDER_YEAR
    cover = release.cover_url or PLACEHOLDER_COVER
    duration = release.duration or PLACEHOLDER_DURATION
    tracklist = release.tracklist or []
    dr_text = (release.dr or PLACEHOLDER_INFO).rstrip("\n")

    parts: list[str] = []
    parts.append(
        single_header(
            root_name=root_name,
            title=title,
            year_val=year_val,
            overall_codec=overall_codec,
            duration=duration,
            cover=cover,
            labels=labels,
        )
    )
    parts.append(single_tracklist(tracklist, labels))
    parts.append(single_dr(dr_text, labels))
    parts.append(about_section(labels))

    return "".join(parts)
