import unittest

from trackerhelper.infra.ffprobe import parse_audio_info, parse_tags


class FfprobeUtilsTests(unittest.TestCase):
    def test_parse_audio_info(self):
        data = {
            "format": {"duration": "123.456"},
            "streams": [
                {"codec_type": "audio", "sample_rate": "44100", "bits_per_sample": "16"},
                {"codec_type": "video"},
            ],
        }
        dur, sr, bit = parse_audio_info(data)
        assert dur is not None
        self.assertAlmostEqual(dur, 123.456)
        self.assertEqual(sr, 44100)
        self.assertEqual(bit, 16)

    def test_parse_tags(self):
        data = {
            "format": {
                "tags": {
                    "ALBUM": "Test Album",
                    "ALBUM ARTIST": "Test Artist",
                    "DATE": "2020",
                }
            }
        }
        tags = parse_tags(data)
        self.assertEqual(tags["album"], "Test Album")
        self.assertEqual(tags["album_artist"], "Test Artist")
        self.assertEqual(tags["date"], "2020")


if __name__ == "__main__":
    unittest.main()
