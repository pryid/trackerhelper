# Data Flow

## stats
1. `app.scan.list_release_scans` finds release folders and audio files.
2. `infra.ffprobe.FfprobeClient` extracts duration/bit depth/sample rate.
3. `app.stats.collect_stats` aggregates per-release and summary stats.
4. `formatting.stats` renders text/JSON/CSV output (optionally per-track).
5. `cli/commands/stats.py` handles CLI flags and prints output.

## release
1. Same scan + ffprobe step as `stats`.
2. `formatting.tracklist.build_tracklist_lines` builds tracklists from filenames.
3. DR logs are matched via `infra.dr` if `--dr-dir` is set.
4. Optional FastPic upload via `infra.cover` (disabled with `--no-cover`).
5. `formatting.bbcode.make_release_bbcode` or `make_single_release_bbcode` renders templates.
6. Missing assets report is rendered via `formatting.release` when requested.

## normalize
1. Scan all folders (including root) for audio files.
2. Use tags (`album`, `album_artist`, `artist`) and folder year to build names.
3. `app.normalize.plan_normalization` computes rename actions.
4. Print changes in dry-run mode, apply renames with `--apply`.

## dedupe
1. Scan all audio files in root folders (`Albums`, `Singles` by default).
2. `infra.fingerprint` fingerprints each file in parallel via `fpcalc` and streams TSV output.
3. `domain.dedupe.find_redundant_releases` finds duplicates and subsets.
4. Reports are written to `_dedupe_reports`, JSON/CSV/JSONL are available via CLI.
5. Optional plan JSON can be written (`--plan-out`) and applied later (`--apply-plan`).
