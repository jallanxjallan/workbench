# Commit Templates

## Compile Commit

```text
compile: <batch-id>

files: <count>

order:
1 <slug>
2 <slug>
...
```

## Submit Commit

```text
submit: <batch-id>

files: <count>

order:
1 <slug>
2 <slug>
...
```

## Guidance

- Preserve the author-selected order exactly.
- Keep `files:` equal to the number of serialized order lines.
- Use `YYYYMMDD-HHMM` for `<batch-id>`.
- Do not stage files inside the macro; the commit acts as a pipeline signal.
