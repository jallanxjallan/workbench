# Pandoc Toolchain

This directory contains the Pandoc toolchain used to normalize source
documents into a consistent intermediate form for downstream processing.

Pandoc is used here as a document normalization engine:

```text
files
  ↓
pandoc reader
  ↓
pandoc AST
  ↓
filters
  ↓
NDJSON emitter
  ↓
asc ingest
```

The tree is organized so filters remain reusable and composable.

`defaults/` contains workflow presets.
`filters/` contains reusable Lua and Python filters grouped by function.
`templates/` contains output templates used by selected Pandoc runs.

NDJSON output is reserved for Autoscribe ingestion pipelines.
