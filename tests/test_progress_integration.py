import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from trackerhelper.app.dedupe_reporting import apply_actions
from trackerhelper.app.normalize import apply_normalization
from trackerhelper.app.release import build_release_bbcode
from trackerhelper.domain.dedupe import DedupeResult
from trackerhelper.domain.models import Release, StatsSummary, Track
from trackerhelper.domain.normalize import NormalizationAction, NormalizationPlan


class RecordingProgress:
    def __init__(self) -> None:
        self.events: list[tuple[str, str | int]] = []

    def start(self, total: int) -> None:
        self.events.append(("start", total))

    def advance(self, step: int = 1) -> None:
        self.events.append(("advance", step))

    def set_description(self, description: str) -> None:
        self.events.append(("description", description))

    def finish(self) -> None:
        self.events.append(("finish", 0))


class ProgressIntegrationTests(unittest.TestCase):
    def test_release_reports_cover_upload_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rel_dir = root / "Albums" / "Artist - 2020 - Album"
            rel_dir.mkdir(parents=True)
            cover_path = rel_dir / "cover.jpg"
            cover_path.write_bytes(b"stub")
            track_path = rel_dir / "01 - Track.flac"
            track_path.write_text("stub", encoding="utf-8")

            release = Release(
                path=rel_dir,
                duration_seconds=123.0,
                track_count=1,
                sample_rates={44100},
                bit_depths={16},
                exts={".flac"},
                tracks=[Track(path=track_path, duration_seconds=123.0, sample_rate=44100, bit_depth=16)],
            )
            summary = StatsSummary(
                total_seconds=123.0,
                total_tracks=1,
                total_sr={44100},
                total_bit={16},
                total_exts={".flac"},
                all_years=[2020],
            )
            progress = RecordingProgress()

            class FakeUploader:
                def upload(self, file_path: Path) -> str:
                    self.uploaded = file_path
                    return "https://img.test/cover.jpg"

            with (
                patch("trackerhelper.app.release.collect_stats", return_value=( [release], summary )),
                patch("trackerhelper.app.release.FastPicCoverUploader", return_value=FakeUploader()),
                patch("trackerhelper.app.release.cover_requests", object()),
            ):
                result = build_release_bbcode(
                    root,
                    {".flac"},
                    include_root=False,
                    dr_dir=None,
                    test_mode=False,
                    no_cover=False,
                    lang="ru",
                    progress=progress,
                )

            self.assertIsNotNone(result)
            descriptions = [value for event, value in progress.events if event == "description"]
            self.assertIn("Preparing releases", descriptions)
            self.assertIn("Preparing releases (1/1): Artist - 2020 - Album", descriptions)
            self.assertIn("Uploading covers (1/1): Artist - 2020 - Album", descriptions)
            starts = [value for event, value in progress.events if event == "start"]
            self.assertIn(1, starts)

    def test_apply_normalization_reports_rename_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "Old Name"
            dst = root / "New Name"
            src.mkdir()
            plan = NormalizationPlan(
                actions=[NormalizationAction(source=src, target=dst)],
                skipped=[],
            )
            progress = RecordingProgress()

            count = apply_normalization(plan, progress=progress)

            self.assertEqual(count, 1)
            self.assertTrue(dst.exists())
            self.assertIn(("description", "Renaming releases"), progress.events)
            self.assertIn(("description", "Renaming releases (1/1): Old Name -> New Name"), progress.events)
            self.assertIn(("advance", 1), progress.events)

    def test_apply_actions_reports_delete_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doomed = root / "Delete Me"
            doomed.mkdir()
            (doomed / "track.flac").write_text("stub", encoding="utf-8")
            result = DedupeResult(
                redundant={doomed},
                duplicate_of={},
                contained_in={},
                unique_count={},
                sizes={},
                post_contained=[],
                unsafe=[],
            )
            progress = RecordingProgress()

            moved, deleted = apply_actions(result, move_to=None, delete=True, quiet=True, progress=progress)

            self.assertEqual((moved, deleted), (0, 1))
            self.assertFalse(doomed.exists())
            self.assertIn(("description", "Deleting releases"), progress.events)
            self.assertIn(("description", "Deleting releases (1/1): Delete Me"), progress.events)
            self.assertIn(("advance", 1), progress.events)


if __name__ == "__main__":
    unittest.main()
