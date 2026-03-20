# Batch Interface

Commit-based batch templates are removed.

## Current Rule

- Obsidian does not create batch commits.
- Obsidian does not create batch tags.
- Workbench owns batch ids, annotated `batch/<id>` tags, and pipeline execution.

## Obsidian Output

Selection macros may only return:

```json
{
  "files": ["path/to/file.md"],
  "slugs": ["prefix.project.hint.identity"],
  "ordered": true
}
```

Slug entries may be empty for valid pre-template notes.
