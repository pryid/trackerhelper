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
