import unittest
from pathlib import Path

from trackerhelper.formatting.tracklist import build_tracklist_lines


class TracklistFormattingTests(unittest.TestCase):
    def test_sorts_numeric_track_numbers(self):
        files = [Path("1 - One.flac"), Path("10 - Ten.flac"), Path("2 - Two.flac")]

        lines = build_tracklist_lines(files, sort=True)

        self.assertEqual(lines, ["01. One", "02. Two", "10. Ten"])

    def test_auto_numbering_skips_used_numbers(self):
        files = [Path("01 - Intro.flac"), Path("Bonus Track.flac"), Path("03 - Outro.flac")]

        lines = build_tracklist_lines(files, sort=True)

        self.assertEqual(lines, ["01. Intro", "03. Outro", "04. Bonus Track"])


if __name__ == "__main__":
    unittest.main()
