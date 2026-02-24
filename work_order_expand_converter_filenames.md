# WORK ORDER
## Expand Converter Filenames & Finalize Internal-Only Architecture

---

## Objective

1. Replace ambiguous converter names:
   - `md_to_json.py`
   - `json_to_md.py`

2. Adopt explicit, domain-accurate filenames:
   - `markdown_to_record.py`
   - `record_to_markdown.py`

3. Remove any remaining CLI exposure.
4. Update imports across the package.
5. Ensure converters remain internal pipeline primitives.

---

# Phase 1 — Rename Files

## Rename in ingest

Rename:

```
workbench/ingest/md_to_json.py
```

to:

```
workbench/ingest/markdown_to_record.py
```

---

## Rename in emit

Rename:

```
workbench/emit/json_to_md.py
```

to:

```
workbench/emit/record_to_markdown.py
```

---

# Phase 2 — Update All Imports

Search entire repository for:

- `md_to_json`
- `json_to_md`

Replace with:

- `markdown_to_record`
- `record_to_markdown`

This includes:

- workbench/cli
- workbench/emit
- workbench/ingest
- tests/
- any shell wrappers invoking python modules

Do NOT leave compatibility aliases unless absolutely required.

---

# Phase 3 — Enforce Pure Module Behavior

Ensure both renamed modules:

- Contain NO argparse usage
- Contain NO Fire usage
- Contain NO `if __name__ == "__main__"` blocks
- Contain NO CLI print usage

They must expose:

- Pure functions
- Stream-based entry functions
- No side-effect global execution

These modules are pipeline primitives only.

---

# Phase 4 — Confirm No CLI Exposure

Verify:

- `bin/` contains ONLY `wkb`
- `wkb --help` does NOT list converter names
- No direct subprocess references to converter filenames exist

Converters must only be reachable via:

```
wkb ingest ...
wkb emit ...
```

---

# Phase 5 — Update Tests

Refactor any tests importing:

```
workbench.ingest.md_to_json
workbench.emit.json_to_md
```

To:

```
workbench.ingest.markdown_to_record
workbench.emit.record_to_markdown
```

Ensure:

- Tests use module imports, not subprocess CLI calls
- Tests validate functional behavior, not filename existence

---

# Phase 6 — Documentation Update

Update references in:

- README.md
- WORKBENCH_STRUCTURE_SUMMARY.md
- Any work order markdown files

Clarify terminology:

"Record" = internal NDJSON structure used by pipeline.

These modules are NOT generic format converters.

---

# Phase 7 — Commit Structure

Commit sequence:

1.
```
STYLE: rename md_to_json → markdown_to_record
STYLE: rename json_to_md → record_to_markdown
```

2.
```
REWRITE: update imports across package
```

3.
```
REWRITE: remove any remaining CLI exposure of converters
```

4.
```
DOCS: update references to new converter names
```

---

# Expected Result

Relevant tree section:

```
bin/
    wkb

workbench/
    ingest/
        markdown_to_record.py
    emit/
        record_to_markdown.py
```

No legacy filenames remain.

---

# Architectural Principle Reinforced

Workbench exposes ONE CLI surface:

```
wkb
```

All format conversion is internal and domain-aware.

Markdown ⇄ Record is not a public tool.
It is a pipeline transformation step.

---

End of work order.

