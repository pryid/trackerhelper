import csv
import json
from io import StringIO
import unittest
from pathlib import Path

from trackerhelper.domain.grouping import group_releases
from trackerhelper.domain.models import Release, StatsSummary, Track
from trackerhelper.formatting.stats import (
    render_stats_csv,
    render_stats_csv_tracks,
    render_stats_json,
    render_stats_text,
)


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
                tracks=[
                    Track(
                        path=self.root / "Albums" / "Alpha" / "01 - Alpha.flac",
                        duration_seconds=60.0,
                        sample_rate=44100,
                        bit_depth=16,
                    )
                ],
            ),
            Release(
                path=self.root / "Singles" / "Beta",
                duration_seconds=120.0,
                track_count=2,
                sample_rates={48000},
                bit_depths={24},
                exts={".wav"},
                tracks=[
                    Track(
                        path=self.root / "Singles" / "Beta" / "01 - Beta.wav",
                        duration_seconds=60.0,
                        sample_rate=48000,
                        bit_depth=24,
                    ),
                    Track(
                        path=self.root / "Singles" / "Beta" / "02 - Beta.wav",
                        duration_seconds=60.0,
                        sample_rate=48000,
                        bit_depth=24,
                    ),
                ],
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
        self.assertIn("Albums/Alpha", text)
        self.assertIn("Singles/Beta", text)
        self.assertIn("Total:", text)

    def test_render_stats_json(self):
        groups = group_releases(self.releases, self.root)
        data = json.loads(render_stats_json(groups, self.summary, self.root))
        self.assertEqual(len(data["groups"]), 2)
        self.assertEqual(data["summary"]["total_tracks"], 3)
        self.assertEqual(data["summary"]["total_releases"], 2)
        self.assertEqual(data["summary"]["scanned_audio_files"], 0)
        self.assertEqual(data["summary"]["unreadable_audio_files"], 0)

    def test_render_stats_json_with_tracks(self):
        groups = group_releases(self.releases, self.root)
        data = json.loads(render_stats_json(groups, self.summary, self.root, include_tracks=True))
        releases = data["groups"][0]["releases"]
        self.assertIn("tracks", releases[0])
        self.assertTrue(releases[0]["tracks"])

    def test_render_stats_text_reports_unreadable_tracks(self):
        release = Release(
            path=self.root / "Albums" / "Broken",
            duration_seconds=60.0,
            track_count=1,
            unreadable_track_count=2,
            sample_rates={44100},
            bit_depths={16},
            exts={".flac"},
            tracks=[
                Track(
                    path=self.root / "Albums" / "Broken" / "01 - Good.flac",
                    duration_seconds=60.0,
                    sample_rate=44100,
                    bit_depth=16,
                )
            ],
        )
        groups = group_releases([release], self.root)

        text = render_stats_text(groups, self.summary, self.root, include_tracks=True)

        self.assertIn("Warning: unreadable tracks skipped: 2", text)

    def test_render_stats_json_includes_unreadable_track_count(self):
        release = Release(
            path=self.root / "Albums" / "Broken",
            duration_seconds=60.0,
            track_count=1,
            unreadable_track_count=2,
            sample_rates={44100},
            bit_depths={16},
            exts={".flac"},
            tracks=[],
        )
        groups = group_releases([release], self.root)

        data = json.loads(render_stats_json(groups, self.summary, self.root))

        self.assertEqual(data["groups"][0]["releases"][0]["unreadable_track_count"], 2)

    def test_render_stats_csv(self):
        csv_text = render_stats_csv(self.releases, self.root)
        rows = list(csv.reader(StringIO(csv_text)))
        self.assertEqual(rows[0][0], "group")
        self.assertEqual(len(rows), 3)

    def test_render_stats_csv_tracks(self):
        csv_text = render_stats_csv_tracks(self.releases, self.root)
        rows = list(csv.reader(StringIO(csv_text)))
        self.assertEqual(rows[0][0], "group")
        self.assertEqual(len(rows), 4)

    def test_render_stats_csv_quotes_special_characters(self):
        release = Release(
            path=self.root / "Albums" / 'Alpha, "Deluxe"',
            duration_seconds=60.0,
            track_count=1,
            sample_rates={44100},
            bit_depths={16},
            exts={".flac"},
            tracks=[],
        )

        rows = list(csv.reader(StringIO(render_stats_csv([release], self.root))))

        self.assertEqual(rows[1][1], 'Albums/Alpha, "Deluxe"')
        self.assertEqual(rows[1][2], 'Albums/Alpha, "Deluxe"')


if __name__ == "__main__":
    unittest.main()
