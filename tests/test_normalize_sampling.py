import tempfile
import unittest
from pathlib import Path

from trackerhelper.app.normalize import TAG_MIN_SAMPLES, TAG_SAMPLE_LIMIT, collect_normalization_inputs
from trackerhelper.app.normalize import plan_normalization
from trackerhelper.infra.ffprobe import TagsReader


class CountingTagsReader(TagsReader):
    def __init__(self, tags: dict[str, str]) -> None:
        self.tags = tags
        self.calls = 0

    def get_tags(self, file_path: Path) -> dict[str, str]:
        self.calls += 1
        return dict(self.tags)


class NormalizeSamplingTests(unittest.TestCase):
    def test_sampling_stops_early_when_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = root / "Albums" / "Sample"
            release.mkdir(parents=True)
            for idx in range(TAG_SAMPLE_LIMIT + 2):
                (release / f"{idx:02d}.flac").touch()

            tags = {"album": "Album", "album_artist": "Artist"}
            reader = CountingTagsReader(tags)
            inputs = collect_normalization_inputs(root, {".flac"}, reader, progress=None)

            self.assertEqual(len(inputs.inputs), 1)
            self.assertGreaterEqual(reader.calls, TAG_MIN_SAMPLES)
            self.assertLess(reader.calls, TAG_SAMPLE_LIMIT)

    def test_plan_normalization_empty_root_has_no_skips(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            plan = plan_normalization(root, {".flac"})

            self.assertEqual(plan.actions, [])
            self.assertEqual(plan.skipped, [])


if __name__ == "__main__":
    unittest.main()
