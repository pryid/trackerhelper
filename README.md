# trackerhelper

English documentation. For Russian, see `README.ru.md`.

Utilities for music discography folders (for example, `Albums/*` and `Singles/*`):

- `dr.ps1` automates foobar2000 Dynamic Range (DR) scans and saves logs per release.
- `trackerhelper` is a CLI that scans releases, summarizes durations, and generates BBCode templates. It can match `*_dr.txt` logs and optionally upload `cover.jpg` to FastPic.

Project docs:
- `docs/ARCHITECTURE.md`
- `docs/DATA_FLOW.md`
- `docs/CONTRIBUTING.md`

Code layout (developer notes):
- `trackerhelper/cli/` CLI parsing and subcommands
- `trackerhelper/app/` use-case orchestration
- `trackerhelper/domain/` pure models and business rules
- `trackerhelper/infra/` external tools and filesystem adapters
- `trackerhelper/formatting/` BBCode and output formatting

## Requirements

### `dr.ps1` (Windows)
WARNING: You must enable automatic DR log saving in foobar2000, otherwise `dr.ps1` will not see the log file.

- Windows 10/11
- PowerShell 5+ (or PowerShell 7+)
- foobar2000 installed (standard or portable)
- DR Meter component installed
- Automatic DR log writing enabled

If DR Meter saves logs to a global folder, `dr.ps1` will not see them because it expects the log inside the release folder (or staging copy when the source is read-only).

### `trackerhelper` (Windows / Linux / macOS)
- Python 3.10+
- `ffprobe` from ffmpeg available in `PATH`
- `requests` (used for FastPic uploads in `release`, installed with the package)
- `rich` (CLI progress output, installed with the package)

Check:
```bash
ffprobe -version
```

## Recommended folder structure

Example:

```text
DiscographyRoot/
  Albums/
    Album Name - 2019/
      01 - Track.flac
      02 - Track.flac
    Another Album - 2021/
      ...
  Singles/
    Single Name - 2020/
      ...
```

Notes:
- Group is the first path segment (for example `Albums` or `Singles`). Other groups are supported and printed separately.
- A release is any folder with at least one supported audio file.
- Year in the release folder name can be `Title - 2024` and is used for BBCode output.

## Install

```bash
pip install trackerhelper
```

Developer install from repo:
```bash
git clone https://github.com/pryid/trackerhelper
cd trackerhelper
pip install -e .
```

On Windows, if PowerShell blocks scripts, you can allow them for the current user:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Usage

More examples: `examples/README.md`.
Progress bars are shown only on TTY; disable with `--no-progress`.

## 1) DR logs via foobar2000 (`dr.ps1`)

### Basic run
```powershell
.\dr.ps1 -Root "D:\Music\Artist"
```

By default the script:
- looks for releases in `Root\Albums\*` and `Root\Singles\*` if those groups exist,
- otherwise treats `Root\*` as releases,
- copies each release into a local staging folder only when the source is read-only (for example SMB),
- runs foobar2000 context menu command `Measure Dynamic Range`,
- waits for a `foo_dr*.txt|log` file inside the release folder (or staging if read-only),
- copies the log into the reports folder.

### Where reports are saved
If `-OutDir` is not set, reports go to:
- `%USERPROFILE%\Music\DR`

File name: `<release_name>_dr.txt` (release name comes from the folder name; invalid characters are replaced with `_`).

### If foobar2000 is portable or not in the default location
```powershell
.\dr.ps1 -Root "D:\Music\Artist" -FoobarPath "D:\Apps\foobar2000\foobar2000.exe"
```

### Common parameters
- `-Root` (required) release root folder
- `-FoobarPath` path to `foobar2000.exe` if auto-detect fails
- `-CommandName` exact context menu command name (default: `"Measure Dynamic Range"`)
- `-Groups` release groups (default: `Albums`, `Singles`)
- `-Ext` audio extensions list
- `-TimeoutSec` max wait per release (default: 1800 seconds)
- `-LogNameRegex` log filename regex (default: `^foo_dr.*\.(txt|log)$`)
- `-OutDir` output folder for final `*_dr.txt`
- `-StageRoot` staging folder location (used only for read-only sources)
- `-KeepStage` keep staging folder (useful for debugging)
- `-ShowFoobar` show foobar window (default is minimized)

### Example for read-only source (SMB)
```powershell
.\dr.ps1 -Root "\\NAS\Music\Artist" -OutDir "D:\Reports\DR"
```

## 2) Duration stats and BBCode (`trackerhelper`)

### Basic stats (grouped output)
```bash
trackerhelper stats "/path/to/DiscographyRoot"
```

Output per release includes:
- duration
- track count (only files where duration was read)
- bit depth and sample rate (if ffprobe returns values)

The end prints `Total: ...`.

### Include tracks directly under root
By default the root is not treated as a release. To include it:
```bash
trackerhelper stats "/path/to/DiscographyRoot" --include-root
```

### Add extra extensions (repeatable)
```bash
trackerhelper stats "/path/to/DiscographyRoot" --ext .ape --ext .tak
```

### Machine-readable stats
```bash
trackerhelper stats "/path/to/DiscographyRoot" --json
trackerhelper stats "/path/to/DiscographyRoot" --csv
```

### Per-track stats
```bash
trackerhelper stats "/path/to/DiscographyRoot" --json --per-track
trackerhelper stats "/path/to/DiscographyRoot" --csv --per-track
```

### Write stats to a file
```bash
trackerhelper stats "/path/to/DiscographyRoot" --json --output "/tmp/stats.json"
```
Output files must be outside the music root.

### Normalize release folder names
Dry run by default:
```bash
trackerhelper normalize "/path/to/DiscographyRoot"
```

Apply changes:
```bash
trackerhelper normalize "/path/to/DiscographyRoot" --apply
```

Formats:
- single release: `Artist - Album (Year)`
- multiple releases: `Year - Artist - Album`

Note: `normalize` uses audio tags for `album` and `artist`, and the year from the folder name. If tags or year are missing, the folder is skipped.

### Generate a BBCode discography template
```bash
trackerhelper release "/path/to/DiscographyRoot"
```

By default BBCode labels are Russian. Use English output:
```bash
trackerhelper release "/path/to/DiscographyRoot" --lang en
```

Disable FastPic cover upload:
```bash
trackerhelper release "/path/to/DiscographyRoot" --no-cover
```

Output file is written to the current working directory as:
- `<root_folder_name>.txt`

Custom output path:
```bash
trackerhelper release "/path/to/DiscographyRoot" --output "/tmp/release.txt"
```
Output files must be outside the music root.

### Report missing covers / DR logs
```bash
trackerhelper release "/path/to/DiscographyRoot" --report-missing
trackerhelper release "/path/to/DiscographyRoot" --report-missing "/tmp/missing_report.txt"
```
Output files must be outside the music root.

The template keeps placeholders like `ROOT_COVER_URL`, `GENRE`, `Service`, `YEAR`.
Russian output uses `ЛЕЙБЛ` for the label placeholder, English output uses `LABEL`.

### Add DR reports to BBCode
If you already have `*_dr.txt` (for example from `dr.ps1`), pass the log directory:
```bash
trackerhelper release "/path/to/DiscographyRoot" --dr-dir "C:\Users\<you>\Music\DR"
```

The tool tries to match DR logs by folder name (several name patterns plus whitespace/dash normalization). If no report is found, BBCode keeps `info`.

### FastPic cover upload (optional)
If the release folder contains `cover.jpg` (case-insensitive), `release` uploads the cover to FastPic and inserts the direct link. If not found or upload fails, it keeps `COVER_URL`.

## 3) Formatting-only mode (`--synthetic`)
```bash
trackerhelper stats "/any/path" --synthetic
trackerhelper release "/any/path" --synthetic
```

## 4) Detect duplicate releases by audio fingerprints (`trackerhelper dedupe`)
```bash
trackerhelper dedupe --roots Albums Singles
```

Options:
- `--move-to DIR` move duplicate releases to a folder
- `--delete` delete duplicate releases (dangerous)
- `--json` output JSON to stdout
- `--csv` output CSV to stdout
- `--jsonl` output JSON Lines to stdout
- `--output PATH` write JSON/CSV/JSONL to a file
- `--plan-out PATH` write a plan JSON to apply later
- `--apply-plan PATH` apply a previously generated plan
- `--dry-run` do not move/delete releases

Output files and reports must be outside the scanned roots.

Note: `--apply-plan` requires either `--move-to` or `--delete`.

`--synthetic` uses synthetic data from `trackerhelper/app/synthetic_dataset.py` and lets you check formatting without real files or ffprobe.

## Troubleshooting

### `dr.ps1`: log does not appear
Most common reasons:
- automatic log writing is not enabled in DR Meter;
- DR Meter saves logs outside the release folder.

For diagnostics:
```powershell
.\dr.ps1 -Root "D:\Music\Artist" -LogNameRegex ".*\.(txt|log)$" -KeepStage
```
Check what files are created inside the release folder (or the staging folder if the source is read-only).

### `dr.ps1`: "cannot find foobar2000.exe"
Provide the path manually:
```powershell
.\dr.ps1 -Root "D:\Music\Artist" -FoobarPath "D:\Apps\foobar2000\foobar2000.exe"
```

### `trackerhelper`: `Error: ffprobe not found`
Install ffmpeg and add it to `PATH` so `ffprobe` is available.

### `trackerhelper`: bit depth / sample rate = `unknown` or `mixed`
This is normal:
- some formats do not provide these fields or ffprobe does not return them;
- a release may contain mixed parameters so it shows `mixed`.
