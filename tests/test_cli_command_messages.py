import argparse
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from trackerhelper.app.release import NoReadableAudioError
from trackerhelper.cli.commands import release as release_cmd
from trackerhelper.cli.commands import stats as stats_cmd
from trackerhelper.domain.models import StatsSummary


class CliCommandMessageTests(unittest.TestCase):
    def test_stats_reports_unreadable_audio(self):
        args = argparse.Namespace(
            json=False,
            csv=False,
            root=".",
            synthetic=False,
            output=None,
            ext=[],
            include_root=False,
            per_track=False,
            no_progress=True,
        )
        summary = StatsSummary(
            total_seconds=0.0,
            total_tracks=0,
            scanned_audio_files=2,
            unreadable_audio_files=2,
        )
        buffer = io.StringIO()

        with (
            patch("trackerhelper.cli.commands.stats.prepare_audio_root", return_value=(Path("/music"), None)),
            patch("trackerhelper.cli.commands.stats.run_with_progress", return_value=([], summary)),
            redirect_stdout(buffer),
        ):
            code = stats_cmd.run(args)

        self.assertEqual(code, 0)
        self.assertIn("Audio files found, but metadata could not be read.", buffer.getvalue())

    def test_release_reports_unreadable_audio(self):
        args = argparse.Namespace(
            root=".",
            synthetic=False,
            ext=[],
            include_root=False,
            no_progress=True,
            dr_dir=None,
            no_cover=False,
            lang="ru",
            output=None,
            report_missing=None,
        )
        buffer = io.StringIO()

        with (
            patch("trackerhelper.cli.commands.release.prepare_audio_root", return_value=(Path("/music"), None)),
            patch(
                "trackerhelper.cli.commands.release.run_with_progress",
                side_effect=NoReadableAudioError("Audio files found, but metadata could not be read."),
            ),
            redirect_stdout(buffer),
        ):
            code = release_cmd.run(args)

        self.assertEqual(code, 0)
        self.assertIn("Audio files found, but metadata could not be read.", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
