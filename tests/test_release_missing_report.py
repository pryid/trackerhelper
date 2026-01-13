import unittest
from pathlib import Path

from trackerhelper.app.release import ReleaseBuildResult
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
        )
        report = render_missing_assets_report(result, root, dr_dir=Path("/dr"))
        self.assertIn("Missing cover.jpg: 1", report)
        self.assertIn("Missing DR reports: 1", report)
        self.assertIn("Albums/Alpha", report)

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


if __name__ == "__main__":
    unittest.main()
