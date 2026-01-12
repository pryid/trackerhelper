from __future__ import annotations

from .models import ReleaseBBCode
from .utils import group_sort_index
from .constants import BBCODE_LABELS, GROUP_TITLES


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
    grouped_releases: dict[str, list[ReleaseBBCode]],
    *,
    lang: str = "ru",
) -> str:
    lang_key = _normalize_lang(lang)
    labels = BBCODE_LABELS[lang_key]
    group_titles = GROUP_TITLES[lang_key]
    yr = f" - {year_range}" if year_range else ""
    parts: list[str] = []

    parts.append(f"[size=24]{root_name}{yr}[/size]\n\n")
    parts.append("[img=right]ROOT_COVER_URL[/img]\n\n")
    parts.append(f"[b]{labels['genre']}[/b]: GENRE\n")
    parts.append(f"[b]{labels['media']}[/b]: WEB [url=https://service.com/123]Service[/url]\n")
    parts.append(f"[b]{labels['label']}[/b]: {labels['label_placeholder']}\n")
    parts.append(f"[b]{labels['year']}[/b]: {year_range or 'YEAR'}\n")
    parts.append(f"[b]{labels['codec']}[/b]: {overall_codec}\n")
    parts.append(f"[b]{labels['rip_type']}[/b]: tracks\n")
    parts.append(f"[b]{labels['source']}[/b]: WEB\n")
    parts.append(f"[b]{labels['duration']}[/b]: {total_duration}\n")

    for group in sorted(grouped_releases.keys(), key=group_sort_index):
        group_title = group_titles.get(group, group)
        parts.append(f'[spoiler="{group_title}"]\n\n')

        for rel in grouped_releases[group]:
            year = rel.year
            title = rel.title
            spoiler_title = f"[{year}] {title}" if year else title

            parts.append(f'[spoiler="{spoiler_title}"]\n')
            parts.append("[align=center]")
            cover = rel.cover_url or "COVER_URL"
            parts.append(f"[img]{cover}[/img]\n")
            parts.append(f"[b]{labels['media']}[/b]: WEB [url=https://service.com/123]Service[/url]\n")
            parts.append(f"{labels['duration']}: {rel.duration}\n")
            parts.append(f'[spoiler="{labels["tracklist"]}"]\n')
            if rel.tracklist:
                parts.append("\n".join(rel.tracklist) + "\n")
            parts.append("[/spoiler]\n")
            parts.append("[/align]\n\n")

            parts.append(f'[spoiler="{labels["dr_report"]}"]\n')
            parts.append("[pre]\n")
            parts.append(((rel.dr or "info").rstrip("\n")) + "\n")
            parts.append("[/pre]\n")
            parts.append("[/spoiler]\n")
            parts.append("[/spoiler]\n\n")

        parts.append("[/spoiler]\n\n")

    parts.append(f'[spoiler="{labels["about"]}"]\n')
    parts.append("info\n")
    parts.append("[/spoiler]\n")

    return "".join(parts)


def make_single_release_bbcode(
    root_name: str,
    year_range: str | None,
    overall_codec: str,
    release: ReleaseBBCode,
    *,
    lang: str = "ru",
) -> str:
    lang_key = _normalize_lang(lang)
    labels = BBCODE_LABELS[lang_key]
    title = str(release.title or "").strip() or "TITLE"
    year_val = release.year or year_range or "YEAR"
    cover = release.cover_url or "COVER_URL"
    duration = release.duration or "00:00:00"
    tracklist = release.tracklist or []
    dr_text = (release.dr or "info").rstrip("\n")

    parts: list[str] = []
    parts.append(f"[size=24]{root_name} / {title}[/size]\n\n")
    parts.append(f"[img=right]{cover}[/img]\n\n")
    parts.append(f"[b]{labels['genre']}[/b]: GENRE\n")
    parts.append(f"[b]{labels['media']}[/b]: WEB [url=https://service.com/123]Service[/url]\n")
    parts.append(f"[b]{labels['label']}[/b]: {labels['label_placeholder']}\n")
    parts.append(f"[b]{labels['year']}[/b]: {year_val}\n")
    parts.append(f"[b]{labels['codec']}[/b]: {overall_codec}\n")
    parts.append(f"[b]{labels['rip_type']}[/b]: tracks\n")
    parts.append(f"[b]{labels['source']}[/b]: WEB\n")
    parts.append(f"[b]{labels['duration']}[/b]: {duration}\n\n")

    parts.append(f'[spoiler="{labels["tracklist"]}"]\n')
    if tracklist:
        parts.append("\n".join(tracklist) + "\n")
    parts.append("[/spoiler]\n\n")

    parts.append(f'[spoiler="{labels["dr_report"]}"]\n')
    parts.append("[pre]\n")
    parts.append(dr_text + "\n")
    parts.append("[/pre]\n")
    parts.append("[/spoiler]\n\n")

    parts.append(f'[spoiler="{labels["about"]}"]\n')
    parts.append("info\n")
    parts.append("[/spoiler]\n")

    return "".join(parts)
