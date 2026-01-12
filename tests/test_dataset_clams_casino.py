import json
import unittest
from pathlib import Path

from trackerhelper.ffprobe_utils import TagsReader
from trackerhelper.tags import release_metadata_from_tags
from trackerhelper.utils import parse_release_title_and_year

DATA_PATH = Path(__file__).resolve().parent / "fixtures" / "clams_casino_dataset.json"


def load_dataset() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


class DatasetFfprobe(TagsReader):
    def __init__(self, tag_map: dict[str, dict[str, str]]) -> None:
        self.tag_map = tag_map

    def get_tags(self, file_path: Path) -> dict[str, str]:
        tags = self.tag_map.get(file_path.as_posix())
        return tags if tags is not None else {}


def build_tag_map(root: Path, releases: list[dict]) -> dict[str, dict[str, str]]:
    tag_map: dict[str, dict[str, str]] = {}
    for rel in releases:
        rel_path = Path(rel["rel_path"])
        for track in rel["tracks"]:
            p = (root / rel_path / track["rel_path"]).as_posix()
            tag_map[p] = track["tags"]
    return tag_map


class ClamsCasinoDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_dataset()
        cls.root = Path("dataset_root")
        cls.tag_map = build_tag_map(cls.root, cls.data["releases"])
        cls.ffprobe = DatasetFfprobe(cls.tag_map)

    def test_groups_present(self):
        groups = {
            Path(rel["rel_path"]).parts[0]
            for rel in self.data["releases"]
            if rel["rel_path"]
        }
        self.assertIn("Albums", groups)
        self.assertIn("Singles", groups)

    def test_parse_year_prefix(self):
        rel = next(
            (
                r
                for r in self.data["releases"]
                if Path(r["rel_path"]).name.startswith("2018 - Lil Peep - 4 Gold Chains")
            ),
            None,
        )
        self.assertIsNotNone(rel, "Expected 2018 Lil Peep release in dataset.")
        assert rel is not None
        name = Path(rel["rel_path"]).name
        title, year = parse_release_title_and_year(name)
        self.assertEqual(year, 2018)
        self.assertEqual(title, "Lil Peep - 4 Gold Chains (feat. Clams Casino)")

    def test_release_metadata_from_tags(self):
        rel = next(
            (
                r
                for r in self.data["releases"]
                if r["rel_path"] == "Albums/Clams Casino - Moon Trip Radio - 2019"
            ),
            None,
        )
        self.assertIsNotNone(rel, "Expected Moon Trip Radio release in dataset.")
        assert rel is not None
        audio_files = [
            self.root / Path(rel["rel_path"]) / track["rel_path"]
            for track in rel["tracks"]
        ]
        artist, album = release_metadata_from_tags(audio_files, self.ffprobe)
        self.assertEqual(artist, "Clams Casino")
        self.assertEqual(album, "Moon Trip Radio")


if __name__ == "__main__":
    unittest.main()
