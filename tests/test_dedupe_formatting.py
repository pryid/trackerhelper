import csv
import json
from io import StringIO
import unittest
from pathlib import Path

from trackerhelper.domain.dedupe import DedupeResult, ReleaseContainment
from trackerhelper.formatting.dedupe import (
    PLAN_VERSION,
    dedupe_result_to_dict,
    iter_dedupe_jsonl,
    render_dedupe_csv,
)


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
        rows = list(csv.reader(StringIO(csv_text)))
        self.assertEqual(rows[0][0], "release")
        self.assertEqual(len(rows), 2)

    def test_render_dedupe_csv_quotes_special_characters(self):
        special = Path('Albums/Alpha, "Deluxe"')
        self.result.redundant = {special}
        self.result.duplicate_of = {special: self.b}
        self.result.sizes = {special: 10, self.b: 10}
        self.result.unique_count = {special: 0, self.b: 0}

        rows = list(csv.reader(StringIO(render_dedupe_csv(self.result))))

        self.assertEqual(rows[1][0], 'Albums/Alpha, "Deluxe"')

    def test_render_dedupe_jsonl(self):
        lines = list(iter_dedupe_jsonl(self.result))
        self.assertEqual(len(lines), 1)
        payload = json.loads(lines[0])
        self.assertEqual(payload["release"], self.a.as_posix())


if __name__ == "__main__":
    unittest.main()
