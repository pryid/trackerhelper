from __future__ import annotations

from pathlib import Path


def make_fake_discography(
    root: Path,
    structure: dict[str, list[str]],
    *,
    track_ext: str = ".flac",
    track_count: int = 1,
    create_cover: bool = False,
) -> list[Path]:
    """Create a simple fake discography tree for tests."""
    created: list[Path] = []
    ext = track_ext if track_ext.startswith(".") else f".{track_ext}"

    for group, releases in structure.items():
        for name in releases:
            rel_dir = root / group / name
            rel_dir.mkdir(parents=True, exist_ok=True)
            for idx in range(1, track_count + 1):
                track_path = rel_dir / f"{idx:02d} - Track{idx}{ext}"
                track_path.write_text("stub", encoding="utf-8")
            if create_cover:
                (rel_dir / "cover.jpg").write_text("stub", encoding="utf-8")
            created.append(rel_dir)

    return created
