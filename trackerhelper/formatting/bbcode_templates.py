from __future__ import annotations

from ..domain.constants import (
    PLACEHOLDER_COVER,
    PLACEHOLDER_GENRE,
    PLACEHOLDER_INFO,
    PLACEHOLDER_MEDIA,
    PLACEHOLDER_RIP_TYPE,
    PLACEHOLDER_ROOT_COVER,
    PLACEHOLDER_SOURCE,
    PLACEHOLDER_YEAR,
)
from ..domain.models import ReleaseBBCode


def release_header(
    *,
    root_name: str,
    year_range: str | None,
    overall_codec: str,
    overall_bit: str,
    overall_sr: str,
    total_duration: str,
    labels: dict[str, str],
) -> str:
    """Return the BBCode header for a multi-release template."""
    year_suffix = f" - {year_range}" if year_range else ""
    return (
        f"[size=24]{root_name}{year_suffix}[/size]\n\n"
        f"[img=right]{PLACEHOLDER_ROOT_COVER}[/img]\n\n"
        f"[b]{labels['genre']}[/b]: {PLACEHOLDER_GENRE}\n"
        f"[b]{labels['media']}[/b]: {PLACEHOLDER_MEDIA}\n"
        f"[b]{labels['label']}[/b]: {labels['label_placeholder']}\n"
        f"[b]{labels['year']}[/b]: {year_range or PLACEHOLDER_YEAR}\n"
        f"[b]{labels['codec']}[/b]: {overall_codec}\n"
        f"[b]{labels['rip_type']}[/b]: {PLACEHOLDER_RIP_TYPE}\n"
        f"[b]{labels['source']}[/b]: {PLACEHOLDER_SOURCE}\n"
        f"[b]{labels['duration']}[/b]: {total_duration}\n"
    )


def group_open(title: str) -> str:
    """Return the opening spoiler tag for a release group."""
    return f'[spoiler="{title}"]\n\n'


def group_close() -> str:
    """Return the closing spoiler tag for a release group."""
    return "[/spoiler]\n\n"


def release_item(release: ReleaseBBCode, labels: dict[str, str]) -> str:
    """Return the BBCode block for a single release entry."""
    year = release.year
    title = release.title
    spoiler_title = f"[{year}] {title}" if year else title
    cover = release.cover_url or PLACEHOLDER_COVER
    tracklist = "\n".join(release.tracklist) + "\n" if release.tracklist else ""
    dr_text = (release.dr or PLACEHOLDER_INFO).rstrip("\n")
    return (
        f'[spoiler="{spoiler_title}"]\n'
        "[align=center]"
        f"[img]{cover}[/img]\n"
        f"[b]{labels['media']}[/b]: {PLACEHOLDER_MEDIA}\n"
        f"{labels['duration']}: {release.duration}\n"
        f'[spoiler="{labels["tracklist"]}"]\n'
        f"{tracklist}"
        "[/spoiler]\n"
        "[/align]\n\n"
        f'[spoiler="{labels["dr_report"]}"]\n'
        "[pre]\n"
        f"{dr_text}\n"
        "[/pre]\n"
        "[/spoiler]\n"
        "[/spoiler]\n\n"
    )


def about_section(labels: dict[str, str]) -> str:
    """Return the final 'about' section."""
    return f'[spoiler="{labels["about"]}"]\n{PLACEHOLDER_INFO}\n[/spoiler]\n'


def single_header(
    *,
    root_name: str,
    title: str,
    year_val: str | int,
    overall_codec: str,
    duration: str,
    cover: str,
    labels: dict[str, str],
) -> str:
    """Return the header for a single-release template."""
    return (
        f"[size=24]{root_name} / {title}[/size]\n\n"
        f"[img=right]{cover}[/img]\n\n"
        f"[b]{labels['genre']}[/b]: {PLACEHOLDER_GENRE}\n"
        f"[b]{labels['media']}[/b]: {PLACEHOLDER_MEDIA}\n"
        f"[b]{labels['label']}[/b]: {labels['label_placeholder']}\n"
        f"[b]{labels['year']}[/b]: {year_val}\n"
        f"[b]{labels['codec']}[/b]: {overall_codec}\n"
        f"[b]{labels['rip_type']}[/b]: {PLACEHOLDER_RIP_TYPE}\n"
        f"[b]{labels['source']}[/b]: {PLACEHOLDER_SOURCE}\n"
        f"[b]{labels['duration']}[/b]: {duration}\n\n"
    )


def single_tracklist(tracklist: list[str], labels: dict[str, str]) -> str:
    """Return the single-release tracklist section."""
    lines = "\n".join(tracklist) + "\n" if tracklist else ""
    return f'[spoiler="{labels["tracklist"]}"]\n{lines}[/spoiler]\n\n'


def single_dr(dr_text: str, labels: dict[str, str]) -> str:
    """Return the single-release DR section."""
    return (
        f'[spoiler="{labels["dr_report"]}"]\n'
        "[pre]\n"
        f"{dr_text}\n"
        "[/pre]\n"
        "[/spoiler]\n\n"
    )
