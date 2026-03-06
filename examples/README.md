# Examples

Basic stats:
```bash
trackerhelper stats "/path/to/DiscographyRoot"
```

Generate a Russian BBCode template without cover uploads:
```bash
trackerhelper release "/path/to/DiscographyRoot" --no-cover
```

Normalize folder names (dry run, then apply):
```bash
trackerhelper normalize "/path/to/DiscographyRoot"
trackerhelper normalize "/path/to/DiscographyRoot" --apply
```

Write JSON stats and a missing-assets report:
```bash
trackerhelper stats "/path/to/DiscographyRoot" --json --output "/tmp/stats.json"
trackerhelper release "/path/to/DiscographyRoot" --no-cover --report-missing "/tmp/missing.txt"
```

Find duplicate releases using absolute paths:
```bash
trackerhelper dedupe --roots "/music/Artist/Albums" "/music/Artist/Singles" --out-dir "/tmp/dedupe_reports" --json --output "/tmp/dedupe.json"
```
