# WORK ORDER
## Refactor Markdown/JSON Converters into Shared Batch-Oriented Python Module

---

## Objective

Eliminate null-delimited markdown streaming and shell-based framing.

Create a shared Python module inside Workbench that:

- Handles Markdown ⇄ Record conversion
- Handles NDJSON batch ingest and emit
- Supports multiple records per invocation (batch-oriented)
- Is importable by:
  - Workbench CLI tools
  - AutoScribe adapters
  - Panflute filters
  - Standalone Python scripts

Shell should orchestrate only. Framing must live entirely in Python.

---

## Architectural Requirements

1. All converters must support MULTIPLE records per invocation.
2. No null-delimited transport.
3. No implicit framing.
4. Input/output format must be deterministic.
5. CLI wrappers must be thin.
6. Package must be installable editable (`pip install -e .`).

---

## Target Package Structure

Workbench/py/workbench/

```
workbench/
  __init__.py

  framing/
    __init__.py
    markdown.py
    ndjson.py
    batch.py

  io/
    __init__.py
    streams.py
```

Workbench must become a proper Python package if not already.

---

## Record Model

Define a canonical record dataclass in framing/markdown.py:

```
@dataclass
class MarkdownRecord:
    metadata: dict
    content: str
```

This is the only record shape used in conversion layers.

---

## Required Functionality

### 1. Markdown → Records (Batch)

Function:

```
def parse_markdown_batch(text: str) -> list[MarkdownRecord]
```

Behavior:

- Accepts a single markdown text stream
- Splits into multiple records using explicit frontmatter boundaries
- Each record must begin with `---` YAML frontmatter
- If no frontmatter is present, treat entire file as one record
- Must preserve content exactly
- No mutation or normalization beyond YAML parsing

Important:
We do NOT rely on null delimiters.
We rely strictly on valid frontmatter boundaries.

---

### 2. Records → Markdown (Batch Emit)

Function:

```
def emit_markdown_batch(records: list[MarkdownRecord]) -> str
```

Behavior:

- Each record emitted with:

---
<yaml>
---

<content>

- Records separated by exactly one blank line
- Deterministic YAML ordering (sort_keys=False)

---

### 3. Records ⇄ NDJSON (Batch)

framing/ndjson.py must implement:

```
def records_to_ndjson(records: list[MarkdownRecord]) -> str
```

- One JSON object per line
- Fields:
  {
    "metadata": {...},
    "content": "..."
  }


```
def ndjson_to_records(text: str) -> list[MarkdownRecord]
```

- Accept full NDJSON text
- Ignore empty lines
- Must be strict JSON (no partial parsing)

---

### 4. Internal Conversion Primitives

Expose module functions as internal primitives:

workbench.ingest.markdown_to_record.markdown_text_to_record_batch

- Accept full markdown batch text
- Convert to NDJSON record batch
- Return text output

workbench.emit.record_to_markdown.record_batch_to_markdown_text

- Accept full NDJSON record batch text
- Emit markdown batch text
- Return text output

NO streaming logic.
NO null delimiters.
NO record guessing.

---

## Pandoc / Panflute Compatibility

Panflute filters must be able to import:

```
from workbench.framing.markdown import parse_markdown_batch
```

No shell delegation for framing.

Lua filters may shell out once per document, not per record.

---

## Error Handling Requirements

- Invalid YAML → raise explicit ValueError
- Invalid JSON → raise explicit ValueError
- No silent fallback behavior
- Raise explicit errors on conversion failure

---

## Determinism Guarantees

- YAML emitted with sort_keys=False
- No timestamp injection
- No auto-generated fields
- No mutation of metadata

Batch input → identical output if round-tripped.

---

## Testing Requirements

Add tests:

1. Single-record round trip
2. Multi-record round trip
3. Mixed frontmatter + content
4. Invalid YAML failure
5. Invalid JSON failure
6. Deterministic output check (string equality)

All tests must pass before commit.

---

## Commit Plan

Commit 1:
- Create package structure
- Implement framing modules
- Add tests

Commit 2:
- Replace CLI wrappers
- Remove null-delimited logic

Commit 3:
- Remove legacy streaming helpers
- Update documentation

---

## Non-Goals

- No ULID generation here
- No batch status updates
- No Redis interaction
- No ledger writes
- No pipeline orchestration

This module performs framing only.

---

## Acceptance Criteria

1. markdown_to_record handles multi-record markdown in one invocation.
2. record_to_markdown handles multi-record NDJSON in one invocation.
3. No xargs required anywhere in pipeline.
4. Pandoc pipelines remain clean.
5. No null-delimited transport remains in repository.

---

## Rationale

All framing must live in Python.
Shell is orchestration only.

This stabilizes the ingest layer and prevents transport corruption under concurrency or mixed-language tooling.

---

END WORK ORDER
