import unittest
from pathlib import Path
from unittest.mock import patch

from trackerhelper.app.stats import collect_stats
from trackerhelper.infra.ffprobe import AudioInfoReader


class StubAudioInfoReader(AudioInfoReader):
    def __init__(self, mapping):
        self.mapping = mapping

    def get_audio_info(self, file_path: Path):
        return self.mapping[file_path]


class StatsCollectionTests(unittest.TestCase):
    def test_collect_stats_excludes_unreadable_tracks_from_release_tracks(self):
        root = Path("/music")
        good = root / "Albums" / "Alpha" / "01 - Good.flac"
        bad = root / "Albums" / "Alpha" / "02 - Bad.flac"
        reader = StubAudioInfoReader(
            {
                good: (60.0, 44100, 16),
                bad: (None, None, None),
            }
        )

        with (
            patch(
                "trackerhelper.app.stats.list_release_scans",
                return_value=[type("Scan", (), {"path": root / "Albums" / "Alpha", "audio_files": [good, bad]})()],
            ),
            self.assertLogs("trackerhelper.app.stats", level="WARNING") as logs,
        ):
            releases, summary = collect_stats(root, {".flac"}, include_root=False, audio_reader=reader)

        self.assertEqual(len(releases), 1)
        self.assertEqual(releases[0].track_count, 1)
        self.assertEqual(releases[0].unreadable_track_count, 1)
        self.assertEqual([track.path for track in releases[0].tracks], [good])
        self.assertEqual(summary.unreadable_audio_files, 1)
        self.assertTrue(any("can't read duration" in line for line in logs.output))


if __name__ == "__main__":
    unittest.main()
