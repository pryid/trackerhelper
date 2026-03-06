import tempfile
import unittest
from pathlib import Path

from trackerhelper.infra.dr import build_dr_index, normalize_name


class DrIndexTests(unittest.TestCase):
    def test_build_dr_index_is_deterministic_for_duplicate_normalized_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "Alpha - dr.txt"
            second = root / "alpha_dr.txt"
            first.write_text("first", encoding="utf-8")
            second.write_text("second", encoding="utf-8")

            index = build_dr_index(root)

            self.assertEqual(index[normalize_name("Alpha")], first)


if __name__ == "__main__":
    unittest.main()
