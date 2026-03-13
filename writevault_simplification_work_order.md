# WORK ORDER
## Simplify `writevault` to Pure Ingest Writer

### Objective

Refactor `writevault` so that it performs **only one task**:

Write new files into a vault's `_ingest` directory from **piped NDJSON records**.

All overwrite logic, slug reconciliation, batch validation, and git checks have been moved to the **writeback worker**.

`writevault` becomes a **stateless NDJSON stream consumer**.

---

# Architectural Change

Previous responsibilities removed from `writevault`:

- overwrite detection
- slug matching
- batch validation
- conditional writeback
- git safety checks
- ASC emit queries

These responsibilities now belong exclusively to:

```
writeback worker
```

`writevault` now performs only:

```
NDJSON -> new file in _ingest
```

---

# Invocation

`writevault` reads **NDJSON from stdin**.

Examples:

```
cat records.ndjson | wkb writevault
```

or

```
asc emit | wkb writevault
```

The command **must never query ASC directly**.

---

# Vault Requirement

`writevault` must only run **inside a Studio vault**.

Detection rule:

Presence of vault marker file:

```
_vault_registry.json
```

If not inside a vault:

```
exit with error
```

Example message:

```
writevault must be run inside a registered Studio vault
```

---

# Output Directory

All files are written to:

```
_vault/_ingest/
```

Create directory if it does not exist.

Example result:

```
Studio/omaf/_ingest/Untitled.md
```

No files may be written outside `_ingest`.

---

# Input Record Format

Each NDJSON record must contain:

Required field:

```
content
```

Optional fields:

```
input_record.slug
input_record.filename_hint
input_record.origin
batch
```

Only `content` is required for file creation.

---

# Slug Handling

`writevault` must **ignore records containing a slug**.

Reason:

Slug-bearing records represent pipeline prompts and must not be written into `_ingest`.

Rule:

```
if record contains slug:
    log warning
    skip record
```

Example log entry:

```
writevault warning: slug detected in ingest stream
slug: omaf.losing_petit
record skipped
```

---

# Filename Resolution

Filename priority:

1. `filename_hint`
2. generated fallback

Fallback naming rule:

```
Untitled.md
Untitled_2.md
Untitled_3.md
...
```

Numbering must avoid collisions inside `_ingest`.

---

# Write Operation

For valid records:

1. resolve filename
2. construct markdown file
3. write content body
4. save file into `_ingest`

Example:

```
Studio/omaf/_ingest/freeberg_notes.md
```

No frontmatter parsing is required.

Content is written exactly as provided.

---

# Error Handling

`writevault` must tolerate malformed input.

| Condition | Action |
|-----------|--------|
| missing content | skip record |
| slug present | log and skip |
| invalid NDJSON | log and continue |
| filesystem error | log and continue |

The command should **not terminate early** unless stdin closes.

---

# Logging

Log file:

```
~/.autoscribe/logs/writevault.log
```

Record:

- records processed
- files written
- skipped records
- warnings

Example summary:

```
writevault
records processed: 12
files written: 10
skipped (slug present): 2
```

---

# CLI Behavior

Command:

```
wkb writevault
```

Behavior:

```
read NDJSON from stdin
write files to _ingest
log summary
exit when stream ends
```

This command **does not run as a worker**.

---

# Module Layout

Suggested implementation:

```
workbench/cli/writevault.py
workbench/lib/vault_writer.py
```

Responsibilities:

| Module | Responsibility |
|--------|---------------|
| writevault CLI | NDJSON stream reader |
| vault_writer | filename resolution and file writing |

---

# IMPLEMENTATION SKELETON

Minimal Python skeleton for Codex implementation.

```
import sys
import json
from pathlib import Path

INGEST_DIR = "_ingest"


def ensure_vault_root():
    marker = Path("_vault_registry.json")
    if not marker.exists():
        raise SystemExit("writevault must be run inside a Studio vault")


def ensure_ingest_dir():
    p = Path(INGEST_DIR)
    p.mkdir(exist_ok=True)
    return p


def next_untitled(path):
    base = path / "Untitled.md"
    if not base.exists():
        return base

    i = 2
    while True:
        candidate = path / f"Untitled_{i}.md"
        if not candidate.exists():
            return candidate
        i += 1


def resolve_filename(record, ingest_dir):
    hint = None

    if "input_record" in record:
        hint = record["input_record"].get("filename_hint")

    if hint:
        return ingest_dir / hint

    return next_untitled(ingest_dir)


def main():

    ensure_vault_root()
    ingest_dir = ensure_ingest_dir()

    written = 0
    skipped_slug = 0

    for line in sys.stdin:

        try:
            record = json.loads(line)
        except Exception:
            continue

        if "content" not in record:
            continue

        slug = None
        if "input_record" in record:
            slug = record["input_record"].get("slug")

        if slug:
            skipped_slug += 1
            continue

        path = resolve_filename(record, ingest_dir)

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(record["content"])
            written += 1
        except Exception:
            continue

    print(f"files written: {written}, skipped (slug present): {skipped_slug}")


if __name__ == "__main__":
    main()
```

