That’s the right sequencing. 👍
You want **three clean refactor passes**, each with a single objective. Codex works far better when the tasks are **orthogonal** like this.

Below are the **three work orders exactly as Codex should receive them**.

------

# Work Order 1

# Introduce Core Ripgrep Query Module

## Objective

Create a **centralized ripgrep query layer** for Studio and refactor writeback to use it. This eliminates filesystem crawling and establishes ripgrep as the canonical artifact index.

Workbench must treat **ripgrep as the Studio query engine**.

------

## Step 1 — Create ripgrep module

Create file:

```
workbench/lib/rg.py
```

Responsibilities:

- execute ripgrep
- parse JSON events
- return structured results

------

### Required function

```
build_slug_index(studio_root: Path) -> dict[str, Path]
```

Behavior:

1. Run ripgrep once over Studio.
2. Capture all frontmatter slug lines.
3. Build mapping:

```
slug → absolute filepath
```

1. Detect duplicate slugs and raise an error.

------

### Ripgrep command

```
rg
  --json
  --pcre2
  --glob '*.md'
  '^slug:\s*(\S+)'
  <studio_root>
```

------

### JSON parsing

Use ripgrep JSON output.

Only process events where:

```
event["type"] == "match"
```

Extract:

```
filepath
slug value
```

Populate dictionary.

------

### Duplicate detection

If the same slug appears twice:

```
raise RipgrepError("duplicate slug detected")
```

------

## Step 2 — Refactor writeback to use slug index

Modify:

```
workbench/write/writeback.py
```

Remove all filesystem scans.

Delete:

```
Path.rglob()
_iter_markdown_paths()
_find_file_by_slug()
```

Replace with:

```
slug_index = build_slug_index(studio_root)
path = slug_index[record.slug]
```

------

## Step 3 — Require Studio root

Writeback must run ripgrep from the Studio root.

Accept:

```
--studio-root
```

Default:

```
~/Studio
```

------

## Step 4 — Preserve existing writeback safety checks

Ensure writeback still validates:

```
record.slug == frontmatter.slug
record.batch_slug == sentinel.batch
```

Abort on mismatch.

------

## Step 5 — Tests

Add tests for:

### slug index generation

- correct slug detection
- duplicate slug error
- ignores non-markdown files

### writeback routing

- correct file resolution
- slug mismatch detection

------

## Commit

```
feat: introduce ripgrep slug index and migrate writeback
```

------

# Work Order 2

# Enforce Document Wrapper for Markdown Parsing

## Objective

Ensure **all markdown parsing and writing uses the Document wrapper**.

Workbench must never manually parse frontmatter or manipulate markdown text.

------

## Step 1 — Audit markdown handling

Search repository for:

```
yaml.safe_load
frontmatter
split('---')
regex frontmatter parsing
manual markdown parsing
```

Identify all occurrences.

------

## Step 2 — Replace with Document wrapper

All markdown operations must use:

```
Document.read_file()
Document.write_text()
Document.inspect_file()
```

Remove manual metadata parsing.

------

## Step 3 — Enforce metadata access pattern

Metadata must be accessed only through:

```
doc.metadata
```

Never parse YAML directly.

------

## Step 4 — Ensure sentinel compatibility

When reading files with sentinels:

```
Document.read_file(path, sentinel_pattern=...)
```

Do not implement custom sentinel handling.

------

## Step 5 — Tests

Add tests confirming:

```
Document correctly preserves frontmatter
sentinel insertion works
content rewrite preserves metadata
```

------

## Commit

```
refactor: enforce Document wrapper for markdown parsing
```

------

# Work Order 3

# Remove Legacy and Over-Engineered Code

## Objective

Remove remaining infrastructure that conflicts with the simplified Workbench architecture.

Workbench should be **minimal plumbing**, not a generic document system.

------

## Step 1 — Remove ULID filename generation

Delete from:

```
workbench/write/common.py
```

Remove:

```
generate_ulid()
generate_random_suffix()
preferred_filename_stem()
ULID constants
```

Workbench must **never invent artifact identities**.

------

## Step 2 — Remove envelope duplication

Delete logic copying full NDJSON records such as:

```
envelope = deepcopy(record)
```

Workbench only needs:

```
content
slug
batch_slug
filename_hint
```

All other fields pass through untouched.

------

## Step 3 — Simplify NDJSON record handling

Remove unnecessary record dataclasses if they exist.

NDJSON should be processed directly as dictionaries.

------

## Step 4 — Remove filesystem crawling utilities

Delete any remaining functions like:

```
scan_vault()
iter_markdown_paths()
Path.rglob scans
```

All vault queries must use:

```
workbench/lib/rg.py
```

------

## Step 5 — Remove redundant helpers

Delete utilities that duplicate functionality already provided by:

```
Document wrapper
ripgrep module
```

Examples:

```
manual metadata parsing
filename uniqueness loops
frontmatter utilities
```

------

## Step 6 — Codebase cleanup

- remove dead imports
- simplify modules
- eliminate unused helpers

------

## Step 7 — Ensure scripts remain small

Each Workbench CLI command should remain:

```
~50–150 lines
```

Maximum.

------

## Commit

```
refactor: remove legacy code and simplify Workbench core
```

------

# Final architecture after these three WOs

Workbench becomes exactly what you intended:

```
Studio filesystem
        ↓
ripgrep query layer
        ↓
Document wrapper
        ↓
simple CLI tools
```

No scanning.
No identity generation.
No markdown parsing logic.

Just **deterministic plumbing**.

------

When this is done, there is **one more extremely powerful step** you will probably want next:

> a **general ripgrep query API** that lets any script run structured Studio queries.

That will eventually replace **half of your auxiliary scripts**.