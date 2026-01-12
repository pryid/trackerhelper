import unittest

from trackerhelper.core.normalize import build_normalized_name, parse_year_from_folder_name


class NormalizeTests(unittest.TestCase):
    def test_parse_year_from_folder_name(self):
        self.assertEqual(parse_year_from_folder_name("Album - 2018"), 2018)
        self.assertEqual(parse_year_from_folder_name("2019 - Album"), 2019)
        self.assertEqual(parse_year_from_folder_name("Reissue 1999 (2010)"), 2010)
        self.assertIsNone(parse_year_from_folder_name("No Year"))

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
