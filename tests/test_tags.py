import unittest

from trackerhelper.domain.tags import select_release_metadata


class ReleaseMetadataFromTagsTests(unittest.TestCase):
    def test_album_artist_preferred(self):
        tags_list = [
            {"album": "Album", "album_artist": "Album Artist", "artist": "Track Artist"},
            {"album": "Album", "artist": "Track Artist 2"},
        ]
        artist, album = select_release_metadata(tags_list)
        self.assertEqual(artist, "Album Artist")
        self.assertEqual(album, "Album")

    def test_artist_fallback_when_album_artist_missing(self):
        tags_list = [
            {"album": "Some Album", "artist": "Main Artist"},
            {"album": "Some Album", "artist": "Main Artist"},
        ]
        artist, album = select_release_metadata(tags_list)
        self.assertEqual(artist, "Main Artist")
        self.assertEqual(album, "Some Album")


if __name__ == "__main__":
    unittest.main()
