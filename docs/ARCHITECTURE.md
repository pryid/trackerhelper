# Architecture

## Overview
- `trackerhelper/cli/main.py` is the entry point. It wires subcommands and logging.
- `trackerhelper/cli/commands/` contains one module per CLI command (`stats`, `release`, `normalize`, `dedupe`).
- `trackerhelper/app/` orchestrates use-cases and side effects (scan, ffprobe, uploads).
- `trackerhelper/domain/` holds pure dataclasses and business logic (`models`, `normalize`, `tags`, `grouping`, `dedupe`).
- `trackerhelper/infra/` contains filesystem + external tool adapters (`scan`, `ffprobe`, `cover`, `dr`, `fingerprint`).
- `trackerhelper/formatting/` owns output formatting (`bbcode`, `bbcode_templates`, `tracklist`).

## External tools
- `ffprobe` is required for `stats`, `release`, and `normalize` (tags, durations).
- `fpcalc` (Chromaprint) is required for `dedupe`.
- `requests` is optional and only used for FastPic cover uploads.

## Layout
- `trackerhelper/cli/` owns CLI parsing and orchestration.
- `trackerhelper/app/` is the application layer.
- `trackerhelper/domain/` and `trackerhelper/formatting/` contain reusable logic.
- `trackerhelper/infra/` is the integration layer for external tools/filesystem.
- `tests/` contains unit tests and dataset fixtures (excluded from sdist).
