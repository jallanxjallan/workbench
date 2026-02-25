# NDJSON Ingest/Convert/Emit Report (Workbench)

## Scope

This report covers NDJSON handling inside the Python package under `workbench/`.

## Executive Summary

- NDJSON ingestion is centralized at `workbench.lib.ndjson.parse_ndjson(...)` for stream-oriented ingest commands, but `workbench.framing.ndjson.ndjson_to_records(...)` performs a separate line parser for framing-level conversion.
- Conversion between markdown batch and NDJSON batch is implemented in `workbench.framing.batch` as thin composition over markdown/document framing and NDJSON framing helpers.
- NDJSON emission occurs both via canonical `emit_ndjson(...)` and direct `json.dumps(...)+ "\n"` in some ingest commands.
- CLI namespace routing is via `wkb -> workbench.cli.main -> workbench.cli.registry`.

## Canonical Data Shape

Two NDJSON shapes are used:

1. Document batch shape (framing/emit path)
   - `{"metadata": <object>, "content": <string>}`
   - Parsed/emitted by `workbench.framing.ndjson`.

2. Pipeline record shape (ingest utilities)
   - Varies by command (examples: `{"path": ...}`, `{"content": ...}`, split output with `output_path`, `section_index`, etc.).
   - Parsed primarily by `workbench.lib.ndjson.parse_ndjson`.

## End-to-End Flow Map

### A) Markdown -> NDJSON (ingest conversion)

1. Entry:
   - `workbench.ingest.markdown_to_record.convert_markdown_stream` ([workbench/ingest/markdown_to_record.py:15](/home/jeremy/Workbench/workbench/ingest/markdown_to_record.py:15))
2. Calls:
   - `markdown_text_to_record_batch` -> `workbench.framing.batch.markdown_to_ndjson` ([workbench/framing/batch.py:9](/home/jeremy/Workbench/workbench/framing/batch.py:9))
3. Conversion:
   - `parse_markdown_batch(text)` -> `list[Document]`
   - `records_to_ndjson(docs)` serializes each document as `{"metadata","content"}` and joins with trailing newline ([workbench/framing/ndjson.py:10](/home/jeremy/Workbench/workbench/framing/ndjson.py:10))

### B) NDJSON -> Markdown (emit conversion)

1. CLI entry:
   - `wkb emit export` -> `workbench.emit.export.main` ([workbench/emit/export.py:43](/home/jeremy/Workbench/workbench/emit/export.py:43))
2. Calls:
   - `export_ndjson_text` -> `ndjson_to_markdown_documents` ([workbench/emit/common.py:24](/home/jeremy/Workbench/workbench/emit/common.py:24))
3. Parsing:
   - `parse_ndjson(io.StringIO(text))` from `workbench.lib.ndjson` ([workbench/lib/ndjson.py:13](/home/jeremy/Workbench/workbench/lib/ndjson.py:13))
4. Emission:
   - Each record is converted via `record_to_markdown(record)` -> `Document(...).write_text()` ([workbench/emit/record_to_markdown.py:27](/home/jeremy/Workbench/workbench/emit/record_to_markdown.py:27))
5. Deprecated alias path:
   - `wkb emit assemble` delegates to export behavior ([workbench/emit/assemble.py:29](/home/jeremy/Workbench/workbench/emit/assemble.py:29))

### C) NDJSON ingest utilities (record transformation path)

1. `wkb ingest split`
   - Ingest: `_read_ndjson` delegates to `parse_ndjson(sys.stdin)` ([workbench/ingest/split.py:18](/home/jeremy/Workbench/workbench/ingest/split.py:18))
   - Transform: splits `content/body/text` by section marker
   - Emit: `_emit(...)` uses `json.dumps(...)+ "\n"` ([workbench/ingest/split.py:100](/home/jeremy/Workbench/workbench/ingest/split.py:100))

2. `wkb ingest inject-metadata`
   - Ingest: `parse_ndjson(sys.stdin)` ([workbench/ingest/inject_metadata.py:39](/home/jeremy/Workbench/workbench/ingest/inject_metadata.py:39))
   - Transform: parses markdown frontmatter in `content`, injects selected keys into `input_record`
   - Emit: `emit_ndjson(record) + "\n"` ([workbench/ingest/inject_metadata.py:54](/home/jeremy/Workbench/workbench/ingest/inject_metadata.py:54))

3. `wkb ingest select records`
   - Ingest: manually parses line-by-line JSON with `json.loads` (not `parse_ndjson`) ([workbench/ingest/_select_records.py:66](/home/jeremy/Workbench/workbench/ingest/_select_records.py:66))
   - Transform: resolves markdown paths, reads files, extracts frontmatter
   - Emit: `print(json.dumps(output_record, ensure_ascii=False))` ([workbench/ingest/_select_records.py:103](/home/jeremy/Workbench/workbench/ingest/_select_records.py:103))

4. `wkb ingest select sentinel`
   - Emits NDJSON path rows `{"path": ...}` via `print(json.dumps(...))` ([workbench/ingest/_select_sentinel.py:98](/home/jeremy/Workbench/workbench/ingest/_select_sentinel.py:98))

## Core Modules and Responsibilities

- NDJSON primitives:
  - [workbench/lib/ndjson.py](/home/jeremy/Workbench/workbench/lib/ndjson.py)
  - Provides `StreamError`, `parse_ndjson`, `emit_ndjson`.
- Framing conversion:
  - [workbench/framing/ndjson.py](/home/jeremy/Workbench/workbench/framing/ndjson.py)
  - Converts `list[Document] <-> NDJSON text` for `metadata/content` schema.
- Batch bridge:
  - [workbench/framing/batch.py](/home/jeremy/Workbench/workbench/framing/batch.py)
  - Markdown batch <-> NDJSON batch composition.
- Emit adapters:
  - [workbench/emit/common.py](/home/jeremy/Workbench/workbench/emit/common.py)
  - [workbench/emit/export.py](/home/jeremy/Workbench/workbench/emit/export.py)
  - [workbench/emit/assemble.py](/home/jeremy/Workbench/workbench/emit/assemble.py)
- Ingest transformers:
  - [workbench/ingest/split.py](/home/jeremy/Workbench/workbench/ingest/split.py)
  - [workbench/ingest/inject_metadata.py](/home/jeremy/Workbench/workbench/ingest/inject_metadata.py)
  - [workbench/ingest/_select_records.py](/home/jeremy/Workbench/workbench/ingest/_select_records.py)
  - [workbench/ingest/_select_sentinel.py](/home/jeremy/Workbench/workbench/ingest/_select_sentinel.py)

## Error Handling Surfaces

- `lib.ndjson.parse_ndjson` raises `StreamError` for:
  - Invalid JSON line (`invalid NDJSON at line N`)
  - Non-object line (`NDJSON record at line N must be an object`)
- `emit.common.ndjson_to_markdown_documents` translates `StreamError` -> `ValueError`, then CLI prints `export: ...` or `assemble: ...`.
- `ingest.split` catches `StreamError` at command boundary and exits with `SystemExit(str(exc))`.
- `ingest.inject_metadata` catches `StreamError`, prints `inject_metadata: ...`, returns `1`.
- `framing.ndjson.ndjson_to_records` raises `ValueError` with its own message format (`invalid JSON on line N: ...`), independent from `lib.ndjson.StreamError`.

## Behavioral Notes from Tests

- Markdown->NDJSON primitive parity is verified:
  - [tests/test_converter_primitives.py:12](/home/jeremy/Workbench/tests/test_converter_primitives.py:12)
- NDJSON framing parser rejects bad JSON lines:
  - [tests/test_framing_batch.py:42](/home/jeremy/Workbench/tests/test_framing_batch.py:42)
- `assemble` and `export` NDJSON adapters are validated for identical output and error behavior:
  - [tests/test_emit_adapter_guardrails.py:29](/home/jeremy/Workbench/tests/test_emit_adapter_guardrails.py:29)

## Current Inconsistencies (Observed)

1. Dual NDJSON parsers:
   - `lib.ndjson.parse_ndjson` and `framing.ndjson.ndjson_to_records` both parse line-delimited JSON with different exception classes/messages.
2. Mixed emission helpers:
   - Some modules use `emit_ndjson`, others write `json.dumps(...)+ "\n"` directly.
3. Record schema is intentionally command-specific in ingest utilities, while framing/emit assumes canonical `metadata/content`.

## Practical Pipeline Examples

- ASC to markdown files:
  - `asc emit <batch> | wkb emit export | wkb writenew --target-dir <dir>`
- Markdown batch to NDJSON batch:
  - `python -m workbench.ingest.markdown_to_record < batch.md`
- NDJSON section splitting:
  - `... | wkb ingest split`

