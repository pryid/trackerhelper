import unittest
from pathlib import Path

from trackerhelper.io.ffprobe_utils import TagsReader
from trackerhelper.core.tags import release_metadata_from_tags


class DummyFfprobe(TagsReader):
    def __init__(self, tags_by_path: dict[Path, dict[str, str]]) -> None:
        self.tags_by_path = tags_by_path

    def get_tags(self, file_path: Path) -> dict[str, str]:
        tags = self.tags_by_path.get(file_path)
        return tags if tags is not None else {}


class ReleaseMetadataFromTagsTests(unittest.TestCase):
    def test_album_artist_preferred(self):
        files = [Path("a.flac"), Path("b.flac")]
        tags_by_path = {
            files[0]: {"album": "Album", "album_artist": "Album Artist", "artist": "Track Artist"},
            files[1]: {"album": "Album", "artist": "Track Artist 2"},
        }
        artist, album = release_metadata_from_tags(files, DummyFfprobe(tags_by_path))
        self.assertEqual(artist, "Album Artist")
        self.assertEqual(album, "Album")

    def test_artist_fallback_when_album_artist_missing(self):
        files = [Path("c.flac"), Path("d.flac")]
        tags_by_path = {
            files[0]: {"album": "Some Album", "artist": "Main Artist"},
            files[1]: {"album": "Some Album", "artist": "Main Artist"},
        }
        artist, album = release_metadata_from_tags(files, DummyFfprobe(tags_by_path))
        self.assertEqual(artist, "Main Artist")
        self.assertEqual(album, "Some Album")


if __name__ == "__main__":
    unittest.main()
