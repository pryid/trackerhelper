import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import make_fake_discography


class CliStatsOutputTests(unittest.TestCase):
    def test_stats_json_output_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = tmp_path / "Music"
            make_fake_discography(root, {"Albums": ["Alpha"]}, track_count=1)
            out_path = tmp_path / "stats.json"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])

            cmd = [
                sys.executable,
                "-m",
                "trackerhelper.cli.main",
                "stats",
                str(root),
                "--synthetic",
                "--json",
                "--per-track",
                "--output",
                str(out_path),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertTrue(out_path.exists())
            data = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertIn("summary", data)


if __name__ == "__main__":
    unittest.main()
