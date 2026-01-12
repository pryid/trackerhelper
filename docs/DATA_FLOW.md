# Data Flow

## stats
1. `io.scan.iter_release_audio_files` finds release folders and audio files.
2. `io.ffprobe_utils.FfprobeClient` extracts duration/bit depth/sample rate.
3. `core.stats.collect_real_stats` aggregates per-release and summary stats.
4. `commands/stats.py` groups releases and prints formatted output.

## release
1. Same scan + ffprobe step as `stats`.
2. `formatting.tracklist.build_tracklist_lines` builds tracklists from filenames.
3. DR logs are matched via `io.dr_utils` if `--dr` is set.
4. Optional FastPic upload via `cover.py` (disabled with `--no-cover`).
5. `bbcode.make_release_bbcode` or `make_single_release_bbcode` renders templates.

## normalize
1. Scan all folders (including root) for audio files.
2. Use tags (`album`, `album_artist`, `artist`) and folder year to build names.
3. Print changes in dry-run mode, apply renames with `--apply`.

## dedupe
1. Scan all audio files in root folders (`Albums`, `Singles` by default).
2. `fpcalc` fingerprints each file in parallel.
3. `dedupe_logic.find_redundant_releases` finds duplicates and subsets.
4. Reports are written to `_dedupe_reports`, then optional move/delete is applied.
