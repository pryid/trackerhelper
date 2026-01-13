from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Protocol


def normalize_tag_key(s: str) -> str:
    """Normalize tag keys to a lower_snake_case style."""
    return "_".join(s.strip().lower().split())


def parse_audio_info(data: dict) -> tuple[float | None, int | None, int | None]:
    """Parse duration/sample rate/bit depth from ffprobe JSON."""
    dur = None
    fmt = data.get("format", {}) or {}
    if "duration" in fmt:
        try:
            dur = float(fmt["duration"])
        except (ValueError, TypeError):
            dur = None

    sr = None
    bit = None
    for st in (data.get("streams") or []):
        if st.get("codec_type") != "audio":
            continue

        try:
            if st.get("sample_rate"):
                sr = int(st["sample_rate"])
        except (ValueError, TypeError):
            sr = None

        b = st.get("bits_per_raw_sample") or st.get("bits_per_sample")
        try:
            if b is not None and str(b).strip() != "":
                bit = int(b)
        except (ValueError, TypeError):
            bit = None
        break

    return (dur, sr, bit)


def parse_tags(data: dict) -> dict[str, str]:
    """Parse tags from ffprobe JSON into a normalized dict."""
    tags_raw = (data.get("format") or {}).get("tags") or {}
    tags: dict[str, str] = {}
    for k, v in tags_raw.items():
        if v is None:
            continue
        key = normalize_tag_key(str(k))
        val = str(v).strip()
        if key and val:
            tags[key] = val
    return tags


class AudioInfoReader(Protocol):
    def get_audio_info(self, file_path: Path) -> tuple[float | None, int | None, int | None]:
        ...


class TagsReader(Protocol):
    def get_tags(self, file_path: Path) -> dict[str, str]:
        ...


class FfprobeClient(AudioInfoReader, TagsReader):
    def __init__(self) -> None:
        self._audio_cache: dict[str, tuple[float | None, int | None, int | None]] = {}
        self._tag_cache: dict[str, dict[str, str]] = {}

    def _run_json(self, args: list[str]) -> dict:
        proc = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return {}
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {}

    def get_audio_info(self, file_path: Path) -> tuple[float | None, int | None, int | None]:
        key = os.fspath(file_path)
        if key in self._audio_cache:
            return self._audio_cache[key]

        data = self._run_json(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration:stream=codec_type,sample_rate,bits_per_sample,bits_per_raw_sample",
                "-of", "json",
                str(file_path),
            ]
        )
        info = parse_audio_info(data) if data else (None, None, None)
        self._audio_cache[key] = info
        return info

    def get_tags(self, file_path: Path) -> dict[str, str]:
        key = os.fspath(file_path)
        if key in self._tag_cache:
            return self._tag_cache[key]

        data = self._run_json(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format_tags",
                "-of", "json",
                str(file_path),
            ]
        )
        tags = parse_tags(data) if data else {}
        self._tag_cache[key] = tags
        return tags
