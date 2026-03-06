from collections import Counter
import unittest
from pathlib import Path

from trackerhelper.domain.dedupe import TrackFingerprint, find_redundant_releases


class DedupeLogicTests(unittest.TestCase):
    def test_repeated_track_count_does_not_create_false_duplicate(self):
        repeated = TrackFingerprint("100", "fp-a")
        release_keys = {
            Path("Albums/Repeated"): Counter({repeated: 2}),
            Path("Albums/Single"): Counter({repeated: 1}),
        }

        result = find_redundant_releases(release_keys)

        self.assertEqual(result.duplicate_of, {})
        self.assertEqual(result.contained_in, {Path("Albums/Single"): Path("Albums/Repeated")})

    def test_repeated_track_count_blocks_false_subset_match(self):
        repeated = TrackFingerprint("100", "fp-a")
        other = TrackFingerprint("200", "fp-b")
        release_keys = {
            Path("Albums/DoubleTrack"): Counter({repeated: 2}),
            Path("Albums/MixedTrack"): Counter({repeated: 1, other: 1}),
        }

        result = find_redundant_releases(release_keys)

        self.assertEqual(result.redundant, set())
        self.assertEqual(result.duplicate_of, {})
        self.assertEqual(result.contained_in, {})


if __name__ == "__main__":
    unittest.main()
