import unittest
from pathlib import Path
from unittest.mock import patch

from trackerhelper.app.release import NoReadableAudioError, ReleaseBuildResult, build_release_bbcode
from trackerhelper.domain.models import StatsSummary
from trackerhelper.formatting.release import render_missing_assets_report


class ReleaseMissingReportTests(unittest.TestCase):
    def test_render_missing_report(self):
        root = Path("/music")
        result = ReleaseBuildResult(
            bbcode="",
            total_releases=2,
            missing_covers=[root / "Albums" / "Alpha"],
            missing_drs=[root / "Albums" / "Alpha"],
            dr_checked=True,
            failed_cover_uploads=[root / "Albums" / "Beta"],
        )
        report = render_missing_assets_report(result, root, dr_dir=Path("/dr"))
        self.assertIn("Missing cover.jpg: 1", report)
        self.assertIn("Failed cover uploads: 1", report)
        self.assertIn("Missing DR reports: 1", report)
        self.assertIn("Albums/Alpha", report)
        self.assertIn("Albums/Beta", report)

    def test_render_missing_report_no_dr(self):
        root = Path("/music")
        result = ReleaseBuildResult(
            bbcode="",
            total_releases=1,
            missing_covers=[],
            missing_drs=[],
            dr_checked=False,
        )
        report = render_missing_assets_report(result, root, dr_dir=None)
        self.assertIn("DR check: disabled", report)
        self.assertIn("Failed cover uploads: 0", report)
        self.assertIn("Cover uploads skipped: no", report)

    def test_render_missing_report_cover_uploads_skipped(self):
        root = Path("/music")
        result = ReleaseBuildResult(
            bbcode="",
            total_releases=1,
            missing_covers=[],
            missing_drs=[],
            dr_checked=False,
            cover_uploads_skipped=True,
        )

        report = render_missing_assets_report(result, root, dr_dir=None)

        self.assertIn("Cover uploads skipped: yes", report)

    def test_build_release_bbcode_raises_when_audio_is_unreadable(self):
        summary = StatsSummary(
            total_seconds=0.0,
            total_tracks=0,
            scanned_audio_files=2,
            unreadable_audio_files=2,
        )

        with patch("trackerhelper.app.release.collect_stats", return_value=([], summary)):
            with self.assertRaises(NoReadableAudioError):
                build_release_bbcode(
                    Path("/music"),
                    {".flac"},
                    include_root=False,
                    dr_dir=None,
                    test_mode=False,
                    no_cover=True,
                    lang="ru",
                )


if __name__ == "__main__":
    unittest.main()
