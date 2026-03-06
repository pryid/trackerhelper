import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from trackerhelper.cli.commands.dedupe import _default_out_dir, _protected_roots


class DedupeCliTests(unittest.TestCase):
    def test_default_out_dir_uses_cwd_when_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            roots = [(base / "Artist" / "Albums").resolve(), (base / "Artist" / "Singles").resolve()]
            for root in roots:
                root.mkdir(parents=True)
            protected_roots = _protected_roots(roots)

            with patch("trackerhelper.cli.commands.dedupe.Path.cwd", return_value=base):
                out_dir = _default_out_dir(roots, protected_roots)

            self.assertEqual(out_dir, (base / "_dedupe_reports").resolve())

    def test_default_out_dir_moves_outside_common_parent_when_needed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            artist_root = base / "Artist"
            roots = [(artist_root / "Albums").resolve(), (artist_root / "Singles").resolve()]
            for root in roots:
                root.mkdir(parents=True)
            protected_roots = _protected_roots(roots)

            with patch("trackerhelper.cli.commands.dedupe.Path.cwd", return_value=artist_root):
                out_dir = _default_out_dir(roots, protected_roots)

            self.assertEqual(out_dir, (base / "Artist_dedupe_reports").resolve())


if __name__ == "__main__":
    unittest.main()
