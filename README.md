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

Top-level commands:

- `wkb writenew <batch-slug>`
- `wkb writeback <batch-slug>`
- `wkb writestream`
- `wkb slug <target_dir> <source_name>`
- `wkb create-project --vault <vault_name> --project "<Title Case Name>"`

`create-project` requirements:

- `vault_name` must be `RealRiting` or `HackWork`
- `project` must be non-empty; mnemonic is auto-derived from title initials

Run `wkb <command> --help` or `wkb <namespace> <command> --help` for command-level usage.

## Public Integration API

`workbench.interop` is the only supported external Python API.

External scripts must import from:

```python
from workbench.interop import Document, to_ndjson, from_ndjson
```

Available symbols:

- `Document`
- `to_ndjson`
- `from_ndjson`

The `framing` namespace is internal and may change without notice.

## Transport Rules

- Markdown input/output represents exactly one document.
- NDJSON is required for multi-record streaming.
- Multi-document markdown streams are not supported.

## Emit vs Write Separation

Canonical composition:

```bash
wkb writenew <batch-slug>
wkb writeback <batch-slug>
asc emit <batch> | wkb emit export | wkb writestream
```

`writenew` and `writeback` resolve record routing from metadata:

1. `target_path`
2. `prompt_slug` prefix (before first `.`)
3. `instruction_slug` prefix (before first `.`)

Vault prefixes map through `workbench/config/vaults.yaml`:

```yaml
hhp: ~/Vaults/HHP
omaf: ~/Vaults/OneManAirForce
websites: ~/Vaults/Websites
```

Batch slugs are treated as opaque timestamp-based execution identifiers.

Layer responsibilities:

| Layer | Responsibility |
| --- | --- |
| `asc emit` | Produce records |
| `wkb emit` | Convert records -> markdown |
| `wkb writenew` / `wkb writeback` | Fetch records, resolve vault routing, persist files |
| `wkb writestream` | Pass markdown through unchanged |

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

## Pre-Commit Enforcement

Workbench commits must go through pre-commit.

```bash
pip install pre-commit
pre-commit install
```

The configured hooks enforce:

- `pytest -q` on every commit
- `ruff` linting with autofix
- `ruff format`
- trailing whitespace cleanup
- end-of-file newline normalization
