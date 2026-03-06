import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from trackerhelper.cli.common import filter_existing_roots, write_output_lines, write_output_text


class CliCommonTests(unittest.TestCase):
    def test_filter_existing_roots_skips_missing_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = root / "Albums"
            existing.mkdir()
            missing = root / "Missing"

            with self.assertLogs("trackerhelper.cli.common", level="WARNING") as logs:
                roots = filter_existing_roots([existing, missing])

            self.assertEqual(roots, [existing])
            self.assertTrue(any("skipping missing root" in line for line in logs.output))

    def test_write_output_text_prints_without_path(self):
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            write_output_text(None, "hello")

        self.assertEqual(buffer.getvalue().strip(), "hello")

    def test_write_output_text_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "nested" / "out.txt"

            write_output_text(out_path, "hello")

            self.assertEqual(out_path.read_text(encoding="utf-8"), "hello")

    def test_write_output_lines_prints_without_path(self):
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            write_output_lines(None, ["a", "b"])

        self.assertEqual(buffer.getvalue().splitlines(), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
