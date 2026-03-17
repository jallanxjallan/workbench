# Compile Batch

Purpose: document the order-safe batch submission behavior used by the compile and submit macros.

## Order Safe Transmission

Selection order from Obsidian is authoritative.

The macro must preserve that order exactly and must not reorder by:

- filename
- slug
- filesystem traversal
- git state

## Current Behavior

When triggered:

1. Read explicit file selections only.
2. Preserve the exact UI selection order.
3. Extract `slug` from each selected file.
4. Abort if any file is missing a slug.
5. Build a normalized commit message.
6. Run `git commit --allow-empty -m "<message>"`.

## Commit Format

Compile:

```text
compile: <batch-id>

files: <count>

order:
1 <slug>
2 <slug>
...
```

Submit:

```text
submit: <batch-id>

files: <count>

order:
1 <slug>
2 <slug>
...
```

## Batch ID

Format:

```text
YYYYMMDD-HHMM
```

## Macro Files

- `_common/macros/compile_batch.js`
- `_common/macros/submit_batch.js`

Difference between Compile and Submit is only the verb.
