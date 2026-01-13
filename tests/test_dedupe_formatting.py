import unittest
from pathlib import Path

from trackerhelper.domain.dedupe import DedupeResult, ReleaseContainment
from trackerhelper.formatting.dedupe import PLAN_VERSION, dedupe_result_to_dict, render_dedupe_csv


class DedupeFormattingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.a = Path("Albums/Alpha")
        self.b = Path("Albums/Beta")
        self.result = DedupeResult(
            redundant={self.a},
            duplicate_of={self.a: self.b},
            contained_in={},
            unique_count={self.a: 0, self.b: 0},
            sizes={self.a: 10, self.b: 10},
            post_contained=[ReleaseContainment(subset=self.a, superset=self.b)],
            unsafe=[],
        )

    def test_dedupe_result_to_dict(self):
        data = dedupe_result_to_dict(self.result, roots=[Path(".")], exts={".flac"})
        self.assertEqual(data["version"], PLAN_VERSION)
        self.assertIn("generated_at", data)
        self.assertEqual(data["redundant"], [self.a.as_posix()])

    def test_render_dedupe_csv(self):
        csv_text = render_dedupe_csv(self.result)
        lines = csv_text.splitlines()
        self.assertEqual(lines[0].split(",")[0], "release")
        self.assertEqual(len(lines), 2)


if __name__ == "__main__":
    unittest.main()
