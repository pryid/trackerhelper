import json
import tempfile
import unittest
from pathlib import Path

from trackerhelper.app.dedupe import apply_plan
from tests.helpers import make_fake_discography


class DedupePlanTests(unittest.TestCase):
    def test_apply_plan_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rel = make_fake_discography(root, {"Albums": ["DeleteMe"]})[0]
            plan_path = root / "plan.json"
            plan_path.write_text(json.dumps({"redundant": [str(rel)]}), encoding="utf-8")

            code, moved, deleted = apply_plan(plan_path, move_to=None, delete=True, quiet=True)
            self.assertEqual(code, 0)
            self.assertEqual(moved, 0)
            self.assertEqual(deleted, 1)
            self.assertFalse(rel.exists())

    def test_apply_plan_move(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rel = make_fake_discography(root, {"Albums": ["MoveMe"]})[0]
            target = root / "Moved"
            plan_path = root / "plan.json"
            plan_path.write_text(json.dumps({"redundant": [str(rel)]}), encoding="utf-8")

            code, moved, deleted = apply_plan(plan_path, move_to=target, delete=False, quiet=True)
            self.assertEqual(code, 0)
            self.assertEqual(moved, 1)
            self.assertEqual(deleted, 0)
            self.assertFalse(rel.exists())
            moved_dirs = list(target.iterdir())
            self.assertTrue(moved_dirs)


if __name__ == "__main__":
    unittest.main()
