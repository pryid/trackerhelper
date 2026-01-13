# Contributing

Thanks for contributing!

## Quick start
1. Create a virtualenv and install dev tools:
   `pip install -e .[dev]`
2. Run tests:
   `python -m unittest discover -s tests`
3. Run lint/type checks:
   `ruff check .`
   `ty check .`

## Project layout
- `trackerhelper/cli/` for CLI commands and parsing.
- `trackerhelper/app/` for use-case orchestration.
- `trackerhelper/domain/` for business logic and dataclasses.
- `trackerhelper/infra/` for filesystem and external tools.
- `trackerhelper/formatting/` for BBCode and output helpers.

## Style notes
- Prefer small helpers with clear names over inline lambdas.
- Keep file operations OS-agnostic (Path over hard-coded separators).
- Update `README.md` when behavior or flags change.
