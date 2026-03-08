# Work Order — Simplify and Formalize `wkb stream`

## Objective

Define the final implementation and scope of the `wkb stream` command after removal of the legacy `workbench.ingest` package.

`wkb stream` must perform **one single task**:

> Read NDJSON records, extract the `content` field from each record, and concatenate those values into a continuous stream of bare Markdown.

The output is intended primarily as **input to Pandoc**.

Example pipeline:

```
asc emit <batch> --ndjson | wkb stream | pandoc ...
```

`wkb stream` must **not** perform any transformation of the markdown itself.

---

# Architectural Contract

Input

```
NDJSON stream
```

Each record is expected to contain:

```
{
  "content": "markdown text"
}
```

Output

```
markdown
markdown
markdown
```

Rules:

1. Preserve **record order** exactly.
2. Emit **only markdown**, never JSON.
3. Skip records without a `content` field.
4. Do **not buffer the entire input**.
5. Maintain **streaming behavior**.

---

# Responsibilities

`wkb stream` is responsible for:

- extracting `content`
- concatenating markdown
- preserving order

`wkb stream` must **not**:

- parse frontmatter
- inspect metadata
- modify markdown
- reorder records
- inject document metadata

All metadata responsibilities belong to:

```
pandoc
```

---

# Required Implementation

Location:

```
workbench/cli/stream.py
```

Dependencies:

```
workbench/lib/ndjson_stream.py
```

Only the streaming iterator should be used.

---

# Canonical Implementation (≈15 lines)

```python
import sys
from workbench.lib.ndjson_stream import iter_ndjson


def stream_markdown(stdin=sys.stdin, stdout=sys.stdout):
    """Stream markdown content extracted from NDJSON records."""

    for record in iter_ndjson(stdin):
        content = record.get("content")
        if not content:
            continue

        stdout.write(content.rstrip())
        stdout.write("\n\n")


if __name__ == "__main__":
    stream_markdown()
```

Properties:

- fully streaming
- constant memory usage
- preserves order
- minimal surface area

---

# CLI Registration

Ensure the command is registered as:

```
wkb stream
```

Example CLI wrapper:

```
workbench/cli/__init__.py
```

or wherever the command registry currently resides.

The command should read **stdin by default**.

---

# Example Usage

### Render batch to PDF

```
asc emit omaf.chapter3 --ndjson \
| wkb stream \
| pandoc -f markdown -t pdf -o chapter3.pdf
```

### Assemble manuscript

```
asc emit omaf.manuscript --ndjson \
| wkb stream \
| pandoc -o manuscript.docx
```

### Inspect raw markdown stream

```
asc emit batch --ndjson | wkb stream
```

---

# Required Code Cleanup

After the ingest removal, review and eliminate redundant NDJSON helpers.

Search for:

```
parse_ndjson
emit_ndjson
_read_ndjson
```

Goal:

Only **one canonical NDJSON reader** should remain:

```
iter_ndjson
```

All streaming code must rely on this implementation.

---

# Tests

Add or confirm tests for:

### Streaming behavior

```
input: 3 NDJSON records
output: concatenated markdown
```

### Order preservation

Records must appear in the output in the same order they appear in the NDJSON stream.

### Missing content

Records without `content` must be ignored.

### Large stream

Ensure no full-file buffering occurs.

---

# Acceptance Criteria

The work order is complete when:

1. `wkb stream` reads NDJSON from stdin.
2. Output is bare markdown only.
3. Record order is preserved.
4. The implementation uses `iter_ndjson`.
5. No redundant NDJSON parsers remain.
6. The command functions correctly in a UNIX pipeline with Pandoc.

---

# Commit Suggestions

```
REWRITE implement minimal streaming markdown emitter (wkb stream)
```

```
STYLE remove redundant NDJSON helpers after ingest removal
```

---

# Final Design Philosophy

Workbench should remain a **plumbing layer**.

```
Workbench  → moves text
Autoscribe → orchestrates transformations
Pandoc     → handles publishing
```

`wkb stream` is therefore intentionally **minimal and streaming-first**.

