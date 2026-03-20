# Compile Batch

Purpose: document the ordered selection handoff used by the compile and submit macros.

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
4. Warn if any file is missing a slug.
5. Return ordered file paths plus slug values.
6. Do not create commits, tags, or batch ids.

## Return Shape

```json
{
  "files": ["path/to/file.md"],
  "slugs": ["prefix.project.hint.identity", ""],
  "ordered": true
}
```

## Macro Files

- `_control/macros/compile_batch.js`
- `_control/macros/submit_batch.js`

Difference between Compile and Submit is only the operator-facing label. Workbench owns pipeline execution.
