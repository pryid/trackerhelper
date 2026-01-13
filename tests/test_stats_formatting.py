import json
import unittest
from pathlib import Path

from trackerhelper.domain.grouping import group_releases
from trackerhelper.domain.models import Release, StatsSummary
from trackerhelper.formatting.stats import render_stats_csv, render_stats_json, render_stats_text


class StatsFormattingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("/music")
        self.releases = [
            Release(
                path=self.root / "Albums" / "Alpha",
                duration_seconds=60.0,
                track_count=1,
                sample_rates={44100},
                bit_depths={16},
                exts={".flac"},
                tracks=[],
            ),
            Release(
                path=self.root / "Singles" / "Beta",
                duration_seconds=120.0,
                track_count=2,
                sample_rates={48000},
                bit_depths={24},
                exts={".wav"},
                tracks=[],
            ),
        ]
        self.summary = StatsSummary(
            total_seconds=180.0,
            total_tracks=3,
            total_sr={44100, 48000},
            total_bit={16, 24},
            total_exts={".flac", ".wav"},
            all_years=[],
        )

    def test_render_stats_text(self):
        groups = group_releases(self.releases, self.root)
        text = render_stats_text(groups, self.summary, self.root)
        self.assertIn("Albums:", text)
        self.assertIn("Singles:", text)
        self.assertIn("Total:", text)

    def test_render_stats_json(self):
        groups = group_releases(self.releases, self.root)
        data = json.loads(render_stats_json(groups, self.summary, self.root))
        self.assertEqual(len(data["groups"]), 2)
        self.assertEqual(data["summary"]["total_tracks"], 3)
        self.assertEqual(data["summary"]["total_releases"], 2)

    def test_render_stats_csv(self):
        csv_text = render_stats_csv(self.releases, self.root)
        lines = csv_text.splitlines()
        self.assertEqual(lines[0].split(",")[0], "group")
        self.assertEqual(len(lines), 3)


if __name__ == "__main__":
    unittest.main()
