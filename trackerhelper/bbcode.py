from __future__ import annotations

from .models import ReleaseBBCode
from .utils import group_sort_index
from .constants import GROUP_TITLES_RU


def make_release_bbcode(
    root_name: str,
    year_range: str | None,
    total_duration: str,
    overall_codec: str,
    overall_bit: str,
    overall_sr: str,
    grouped_releases: dict[str, list[ReleaseBBCode]],
) -> str:
    yr = f" - {year_range}" if year_range else ""
    parts: list[str] = []

    parts.append(f"[size=24]{root_name}{yr}[/size]\n\n")
    parts.append("[img=right]ROOT_COVER_URL[/img]\n\n")
    parts.append("[b]Жанр[/b]: GENRE\n")
    parts.append("[b]Носитель[/b]: WEB [url=https://service.com/123]Service[/url]\n")
    parts.append("[b]Издатель (лейбл)[/b]: ЛЕЙБЛ\n")
    parts.append(f"[b]Год издания[/b]: {year_range or 'YEAR'}\n")
    parts.append(f"[b]Аудиокодек[/b]: {overall_codec}\n")
    parts.append("[b]Тип рипа[/b]: tracks\n")
    parts.append("[b]Источник[/b]: WEB\n")
    parts.append(f"[b]Продолжительность[/b]: {total_duration}\n")

    for group in sorted(grouped_releases.keys(), key=group_sort_index):
        ru_title = GROUP_TITLES_RU.get(group, group)
        parts.append(f'[spoiler="{ru_title}"]\n\n')

        for rel in grouped_releases[group]:
            year = rel.year
            title = rel.title
            spoiler_title = f"[{year}] {title}" if year else title

            parts.append(f'[spoiler="{spoiler_title}"]\n')
            parts.append("[align=center]")
            cover = rel.cover_url or "COVER_URL"
            parts.append(f"[img]{cover}[/img]\n")
            parts.append("[b]Носитель[/b]: WEB [url=https://service.com/123]Service[/url]\n")
            parts.append(f"Продолжительность: {rel.duration}\n")
            parts.append('[spoiler="Треклист"]\n')
            parts.extend(line + "\n" for line in rel.tracklist)
            parts.append("[/spoiler]\n")
            parts.append("[/align]\n\n")

            parts.append('[spoiler="Динамический отчет (DR)"]\n')
            parts.append("[pre]\n")
            parts.append(((rel.dr or "info").rstrip("\n")) + "\n")
            parts.append("[/pre]\n")
            parts.append("[/spoiler]\n")
            parts.append("[/spoiler]\n\n")

        parts.append("[/spoiler]\n\n")

    parts.append('[spoiler="Об исполнителе (группе)"]\n')
    parts.append("info\n")
    parts.append("[/spoiler]\n")

    return "".join(parts)


def make_single_release_bbcode(
    root_name: str,
    year_range: str | None,
    overall_codec: str,
    release: ReleaseBBCode,
) -> str:
    title = str(release.title or "").strip() or "TITLE"
    year_val = release.year or year_range or "YEAR"
    cover = release.cover_url or "COVER_URL"
    duration = release.duration or "00:00:00"
    tracklist = release.tracklist or []
    dr_text = (release.dr or "info").rstrip("\n")

    parts: list[str] = []
    parts.append(f"[size=24]{root_name} / {title}[/size]\n\n")
    parts.append(f"[img=right]{cover}[/img]\n\n")
    parts.append("[b]Жанр[/b]: GENRE\n")
    parts.append("[b]Носитель[/b]: WEB [url=https://service.com/123]Service[/url]\n")
    parts.append("[b]Издатель (лейбл)[/b]: ЛЕЙБЛ\n")
    parts.append(f"[b]Год издания[/b]: {year_val}\n")
    parts.append(f"[b]Аудиокодек[/b]: {overall_codec}\n")
    parts.append("[b]Тип рипа[/b]: tracks\n")
    parts.append("[b]Источник[/b]: WEB\n")
    parts.append(f"[b]Продолжительность[/b]: {duration}\n\n")

    parts.append('[spoiler="Треклист"]\n')
    parts.extend(line + "\n" for line in tracklist)
    parts.append("[/spoiler]\n\n")

    parts.append('[spoiler="Динамический отчет (DR)"]\n')
    parts.append("[pre]\n")
    parts.append(dr_text + "\n")
    parts.append("[/pre]\n")
    parts.append("[/spoiler]\n\n")

    parts.append('[spoiler="Об исполнителе (группе)"]\n')
    parts.append("info\n")
    parts.append("[/spoiler]\n")

    return "".join(parts)
