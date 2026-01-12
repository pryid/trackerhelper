from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Protocol

from .constants import TAG_KEYS_ALBUM, TAG_KEYS_ALBUM_ARTIST, TAG_KEYS_ARTIST
from .utils import clean_name_part


def tag_value(tags: dict[str, str], keys: list[str]) -> str | None:
    for k in keys:
        v = tags.get(k)
        if v:
            return v.strip()
    return None


def count_sort_key(item: tuple[str, int]) -> tuple[int, int, str]:
    val, count = item
    return (count, -len(val), val.lower())


def most_common_str(values: list[str]) -> str | None:
    if not values:
        return None
    counts = Counter(values)
    return max(counts.items(), key=count_sort_key)[0]


class TagsReader(Protocol):
    def get_tags(self, path: Path) -> dict[str, str]:
        ...


def release_metadata_from_tags(
    audio_files: list[Path],
    ffprobe: TagsReader,
) -> tuple[str | None, str | None]:
    album_values: list[str] = []
    album_artist_values: list[str] = []
    artist_values: list[str] = []

    for f in audio_files:
        tags = ffprobe.get_tags(f)
        if not tags:
            continue

        album = tag_value(tags, TAG_KEYS_ALBUM)
        if album:
            album_values.append(clean_name_part(album))

        album_artist = tag_value(tags, TAG_KEYS_ALBUM_ARTIST)
        if album_artist:
            album_artist_values.append(clean_name_part(album_artist))

        artist = tag_value(tags, TAG_KEYS_ARTIST)
        if artist:
            artist_values.append(clean_name_part(artist))

    album = most_common_str(album_values)
    artist = most_common_str(album_artist_values) or most_common_str(artist_values)
    return artist, album
