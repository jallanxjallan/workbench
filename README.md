# Workbench

Runtime toolchain repository for CLI stream adapters, shell integration, vault workflows, and backup orchestration.

## CLI Surface

Workbench exposes one operator entrypoint:

```bash
wkb
```

Namespaces:

- `wkb ingest`
- `wkb emit`
- `wkb project`
- `wkb backup`

Top-level write commands:

- `wkb writenew --target-dir <path>`
- `wkb writeback`
- `wkb writestream`

Run `wkb <command> --help` or `wkb <namespace> <command> --help` for command-level usage.

## Batch Framing

Workbench framing is Python-native and batch-oriented.

- Import surface:
  - `workbench.framing.markdown.parse_markdown_batch`
  - `workbench.framing.markdown.emit_markdown_batch`
  - `workbench.framing.ndjson.records_to_ndjson`
  - `workbench.framing.ndjson.ndjson_to_records`
- Internal conversion primitives:
  - `workbench.ingest.markdown_to_record.markdown_text_to_record_batch`
  - `workbench.emit.record_to_markdown.record_to_markdown`
  - `workbench.emit.assemble.assemble_markdown_documents`

`record` means the internal NDJSON structure used by the pipeline. These modules are internal primitives, not public CLI commands.

Null-delimited framing is not used.

## Emit vs Write Separation

Canonical composition:

```bash
asc emit <batch> | wkb emit export | wkb writenew --target-dir notes/output
asc emit <batch> | wkb emit export | wkb writeback
asc emit <batch> | wkb emit export | wkb writestream
```

Layer responsibilities:

| Layer | Responsibility |
| --- | --- |
| `asc emit` | Produce records |
| `wkb emit` | Convert records -> markdown |
| `wkb write*` | Persist or stream markdown |

## Pandoc Integration Policy

Workbench does **not** own Pandoc filters/templates internally.

- Pandoc assets and filter logic live in the standalone `pandoc-toolchain` repository.
- Workbench invokes Pandoc via CLI only.
- Workbench does not import Pandoc filter modules from its own Python package.

### Local Symlink For Editing

Workbench may expose a local convenience symlink:

```bash
cd ~/Workbench
ln -sfn "$HOME/.local/share/pandoc" pandoc-data
```

`pandoc-data` is local-only and ignored by git. It is not owned by Workbench.

### CLI Invocation Pattern

Use explicit data-dir wiring:

```bash
pandoc "$INPUT.md" \
  --data-dir "$PWD/pandoc-data" \
  --template default \
  --lua-filter "$PWD/pandoc-data/filters/lua/content-filtering/filter_components.lua" \
  -o "$OUTPUT.pdf"
```

Optional shell helper:

```bash
wb-pandoc() {
  pandoc --data-dir "$PWD/pandoc-data" "$@"
}
```

## Ownership Boundaries

- In scope: CLI orchestration, stream adapters, shell lifecycle, vault logic, backups.
- Out of scope: Pandoc filter/template/reference implementation.
