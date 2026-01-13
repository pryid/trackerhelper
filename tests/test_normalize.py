import unittest

from trackerhelper.domain.normalize import build_normalized_name
from trackerhelper.domain.utils import parse_year_from_text


class NormalizeTests(unittest.TestCase):
    def test_parse_year_from_folder_name(self):
        self.assertEqual(parse_year_from_text("Album - 2018"), 2018)
        self.assertEqual(parse_year_from_text("2019 - Album"), 2019)
        self.assertEqual(parse_year_from_text("Reissue 1999 (2010)"), 2010)
        self.assertIsNone(parse_year_from_text("No Year"))

    def test_build_normalized_name_single(self):
        self.assertEqual(
            build_normalized_name("Artist", "Album", 2020, True),
            "Artist - Album (2020)",
        )

    def test_build_normalized_name_multi(self):
        self.assertEqual(
            build_normalized_name("Artist", "Album", 2020, False),
            "2020 - Artist - Album",
        )

    def test_build_normalized_name_missing(self):
        self.assertIsNone(build_normalized_name(None, "Album", 2020, True))
        self.assertIsNone(build_normalized_name("Artist", None, 2020, True))
        self.assertIsNone(build_normalized_name("Artist", "Album", None, True))


if __name__ == "__main__":
    unittest.main()
