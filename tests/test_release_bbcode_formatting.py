from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from trackerhelper.app.release import build_release_bbcode
from trackerhelper.domain.models import Release, StatsSummary, Track


def _make_release(path: Path, *, duration_seconds: float = 60.0) -> Release:
    return Release(
        path=path,
        duration_seconds=duration_seconds,
        track_count=1,
        exts={".flac"},
        tracks=[Track(path=path / "01 - Track.flac", duration_seconds=duration_seconds)],
    )


class ReleaseBBCodeFormattingTests(unittest.TestCase):
    def test_root_level_releases_do_not_get_extra_group_spoilers(self):
        root = Path("/music/Discography")
        releases = [
            _make_release(root / "2004 - Ideologia"),
            _make_release(root / "2005 - Atlantida"),
        ]
        summary = StatsSummary(
            total_seconds=120.0,
            total_tracks=2,
            total_exts={".flac"},
            all_years=[2004, 2005],
        )

        with patch("trackerhelper.app.release.collect_stats", return_value=(releases, summary)):
            result = build_release_bbcode(
                root,
                {".flac"},
                include_root=True,
                dr_dir=None,
                test_mode=False,
                no_cover=True,
                lang="ru",
            )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertNotIn('[spoiler="2004 - Ideologia"]', result.bbcode)
        self.assertNotIn('[spoiler="2005 - Atlantida"]', result.bbcode)
        self.assertIn('[spoiler="[2004] Ideologia"]', result.bbcode)
        self.assertIn('[spoiler="[2005] Atlantida"]', result.bbcode)

    def test_grouped_releases_keep_group_spoiler(self):
        root = Path("/music/Discography")
        releases = [
            _make_release(root / "Albums" / "2004 - Ideologia"),
            _make_release(root / "Albums" / "2005 - Atlantida"),
        ]
        summary = StatsSummary(
            total_seconds=120.0,
            total_tracks=2,
            total_exts={".flac"},
            all_years=[2004, 2005],
        )

        with patch("trackerhelper.app.release.collect_stats", return_value=(releases, summary)):
            result = build_release_bbcode(
                root,
                {".flac"},
                include_root=True,
                dr_dir=None,
                test_mode=False,
                no_cover=True,
                lang="ru",
            )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn('[spoiler="Альбомы"]', result.bbcode)
        self.assertIn('[spoiler="[2004] Ideologia"]', result.bbcode)
        self.assertIn('[spoiler="[2005] Atlantida"]', result.bbcode)


if __name__ == "__main__":
    unittest.main()
