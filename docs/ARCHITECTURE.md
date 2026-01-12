# Architecture

## Overview
- `trackerhelper/cli.py` is the single entry point. It wires subcommands and logging.
- `trackerhelper/commands/` contains one module per CLI command (`stats`, `release`, `normalize`, `dedupe`).
- `trackerhelper/core/` holds core dataclasses and business logic (`models`, `stats`, `normalize`, `tags`, `utils`, `grouping`).
- `trackerhelper/io/` contains filesystem + external tool helpers (`scan`, `ffprobe_utils`, `cover`, `dr_utils`).
- `trackerhelper/formatting/` owns output formatting (`bbcode`, `bbcode_templates`, `tracklist`).
- `trackerhelper/dedupe_*.py` splits fingerprinting, scan helpers, logic, and reporting.

## External tools
- `ffprobe` is required for `stats`, `release`, and `normalize` (tags, durations).
- `fpcalc` (Chromaprint) is required for `dedupe`.
- `requests` is optional and only used for FastPic cover uploads.

## Layout
- `trackerhelper/commands/` owns CLI parsing and orchestration.
- `trackerhelper/core/`, `trackerhelper/io/`, and `trackerhelper/formatting/` contain reusable logic.
- `tests/` contains unit tests and dataset fixtures (excluded from sdist).
