# Atomic Ingest Pipelines

Legacy ingest orchestrators are frozen under `dev/legacy_ingest/` and are no
longer exposed by `w`.

Use explicit pipelines composed from atomic commands.

## External Markdown File

```sh
cat note.md \
| w md_to_json \
| w inject_metadata \
| w strip_frontmatter \
| asc ingest calls
```

## Vault Content

```sh
asc select sentinel \
| asc select records \
| asc ingest calls
```

## Optional Validation Steps

```sh
cat note.md \
| w md_to_json \
| w validate_frontmatter \
| w detect_sentinel
```

These commands are intentionally single-purpose and stream-safe:
- `w md_to_json`
- `w wrap_ndjson`
- `w strip_frontmatter`
- `w inject_metadata`
- `w validate_frontmatter`
- `w detect_sentinel`
- `w normalize_path`
- `w split_by_regex`
