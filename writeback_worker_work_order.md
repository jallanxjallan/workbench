# WORK ORDER

## Non-Implementation Notice

This work order is intentionally deferred and should not be implemented right now.

Reason:
- the ASC emit interface is likely to change during the upcoming Autoscribe refactor
- implementing against the current inferred contract would create churn and rework
- the command surface, polling contract, and write-finalization handshake should be revisited once the refactor settles

Current decision:
- no `writeback` worker implementation is being added in this pass
- no CLI entrypoints are being added in this pass
- this document remains as a design placeholder only

## Implement `writeback` Worker in Workbench

### Objective

Implement a long‑running **writeback worker** in Workbench that reconciles completed ASC emit records with files in Studio vaults and performs safe writeback operations.

The worker must:

- poll ASC for finished emit records
- map emit slugs to vault files
- validate batch provenance via git
- refuse writes when files are dirty
- write results back into vault files
- mark emit records as written
- log anomalies

The worker runs continuously and maintains **persistent indices** to avoid repeated filesystem scans.

---

# Architectural Role

The writeback worker is a reconciliation service between three systems:

| System | Role |
|------|------|
| Studio vaults | editorial artifacts |
| ASC emit | pipeline outputs |
| Git | provenance verification |

Writeback is permitted **only when these systems agree**.

---

# Safety Invariants

A writeback may occur **only if all conditions pass**:

1. slug exists in vault index
2. emit record contains slug
3. emit batch matches vault git batch
4. file working tree is clean

If any condition fails, writeback must be skipped.

Human edits always take precedence over automated writes.

---

# Worker Command

CLI entrypoint:

```
wkb writeback
```

Behavior:

- start long‑running worker loop
- poll ASC emit every 60 seconds
- reconcile results
- perform writebacks

---

# Worker State Directory

```
~/.autoscribe/workers/writeback/
```

Files:

```
slug_index.ndjson
worker_state.json
writeback.log
```

---

# Persistent Slug Index

Slug index maps slugs to filepaths.

Format (NDJSON):

```
{"slug":"omaf.losing_petit","path":"Studio/omaf/chapters/losing_petit.md"}
{"slug":"omaf.freeberg_intro","path":"Studio/omaf/chapters/freeberg_intro.md"}
```

The index is a **cache**, not an authority.

---

# Building the Slug Index

Initial build uses ripgrep.

Equivalent command:

```
rg '^slug:' Studio -g '*.md'
```

Parse results into:

```
slug -> filepath
```

Persist as `slug_index.ndjson`.

---

# Worker Loop

Worker loop interval:

```
60 seconds
```

Loop steps:

1. poll ASC emit for pending records
2. extract slugs from emit records
3. verify slug presence in index
4. rebuild index if necessary
5. perform reconciliation
6. write results
7. sleep

---

# Emit Poll

Worker queries ASC for emit records:

Criteria:

```
status = finished
written = false
```

Expected fields:

```
slug
batch
content
emit_ulid
```

Records without `slug` must be discarded.

---

# Slug Index Validation

For each emit slug:

```
if slug not in slug_index
```

Then:

```
rebuild slug index
```

Recheck.

If slug still missing after rebuild:

Log anomaly and skip record.

---

# Anomaly Logging

If slug remains missing after index rebuild:

Example:

```
WRITEBACK WARNING

slug not found in vault after index rebuild

slug: omaf.losing_petit
batch: omaf.losing_petit
emit_ulid: 01J8K...
```

Log file:

```
~/.autoscribe/workers/writeback/writeback.log
```

Do not crash worker.

Log each missing slug only once per session.

---

# File Resolution

Resolve filepath via:

```
filepath = slug_index[slug]
```

Worker must remain **vault‑agnostic**.

---

# Git Validation

Before writeback, verify batch provenance.

Git must confirm:

```
emit.batch == vault_batch
```

If batch mismatch:

```
skip record
```

---

# Dirty File Check

Equivalent command:

```
git status --porcelain path
```

If file is modified:

```
skip writeback
```

Emit record remains pending.

---

# Writeback Operation

If all checks pass:

1. load target file
2. preserve existing frontmatter
3. replace document body with emit content
4. write file
5. stage file with git

---

# Emit Record Finalization

After successful writeback:

Worker must notify ASC:

```
written = true
```

---

# Worker Logging

Each cycle logs summary:

```
writeback cycle
pending emits: 12
written: 3
skipped dirty: 2
skipped batch mismatch: 2
```

Logs appended to:

```
writeback.log
```

---

# Manual Override Command

Separate command:

```
wkb overwrite <file>
```

Behavior:

1. read slug from file
2. query ASC emit for matching record
3. verify batch match
4. show confirmation prompt
5. overwrite file
6. mark emit record written

---

# Module Layout

```
workbench/workers/writeback_worker.py
workbench/workers/writeback_core.py
workbench/workers/slug_index.py
workbench/workers/emit_client.py
```

Responsibilities:

| Module | Responsibility |
|------|------|
| writeback_worker | main loop |
| writeback_core | validation + write logic |
| slug_index | index creation and lookup |
| emit_client | ASC emit polling |

---

# Expected Result

After implementation:

- ASC emit records automatically reconcile to vault files
- human edits are always protected
- writeback occurs only when provenance matches
- the system runs continuously with near‑zero resource usage

---

# IMPLEMENTATION SKELETON

Below is the minimal algorithmic skeleton for the worker loop.

```
import time
from slug_index import load_index, rebuild_index
from emit_client import fetch_pending_emit
from writeback_core import (
    resolve_file,
    file_dirty,
    batch_matches,
    perform_writeback,
    mark_emit_written,
)
from logger import log_cycle, log_warning

POLL_INTERVAL = 60


def run_worker():

    slug_index = load_index()
    reported_missing = set()

    while True:

        emit_records = fetch_pending_emit()

        written = 0
        skipped_dirty = 0
        skipped_batch = 0

        for record in emit_records:

            slug = record.get("slug")
            batch = record.get("batch")

            if not slug:
                continue

            if slug not in slug_index:

                slug_index = rebuild_index()

                if slug not in slug_index:

                    if slug not in reported_missing:
                        log_warning(
                            "slug missing after rebuild",
                            slug=slug,
                            batch=batch,
                            emit_ulid=record.get("emit_ulid"),
                        )
                        reported_missing.add(slug)

                    continue

            path = resolve_file(slug_index, slug)

            if file_dirty(path):
                skipped_dirty += 1
                continue

            if not batch_matches(path, batch):
                skipped_batch += 1
                continue

            perform_writeback(path, record["content"])
            mark_emit_written(record)

            written += 1

        log_cycle(
            pending=len(emit_records),
            written=written,
            skipped_dirty=skipped_dirty,
            skipped_batch=skipped_batch,
        )

        time.sleep(POLL_INTERVAL)
```
