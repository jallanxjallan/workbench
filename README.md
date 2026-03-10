# Workbench

Runtime toolchain repository for CLI stream flows, shell integration, and vault workflows.

## CLI Surface

Workbench exposes one operator entrypoint:

```bash
wkb
```

Namespaces:

- `wkb vault`

Top-level commands:

- `wkb write-new --schema <name> --path <dir>`
- `wkb writenew [--folder <name>] [--template <name>]`
- `wkb write-back [--studio-root <path>]`
- `wkb write-stream`
- `wkb stream`
- `wkb scan-sentinel [paths...]`
- `wkb compile-assets [--studio-root <path>]`
- `wkb generate-slugs [--write]`
- `wkb create-vault <vault-name-or-path>`

Obsidian scaffolding roots used by `create-vault`:

- `~/Workbench/obsidian/vault-template` (template source)
- `~/Workbench/obsidian/vault-common` (symlink target for `_common`)
- Per-vault registry file: `_vault_registry` (single JSON object)
- Per-vault template root: `_common/templates` (pure Markdown templates)
- Per-vault template script: `_common/scripts/new_note.js`

Vault template command:

- `wkb vault template apply --template <template_name> --files file1.md file2.md`

## Template Workflow (Registry-Free Note Creation)

- Templates are discovered from the filesystem under `_common/templates/`.
- Templates remain pure Markdown and must not contain Templater commands.
- Note creation uses `_common/scripts/new_note.js` (Templater picker) and class semantics come from frontmatter `class`.
- Folder routing by class is intentionally disabled.

Run `wkb <command> --help` or `wkb <namespace> <command> --help` for command-level usage.

`wkb stream` reads NDJSON from stdin, extracts each record `content`, and writes a concatenated
bare markdown stream (for example: `asc emit <batch> --ndjson | wkb stream | pandoc ...`).

`wkb generate-slugs` scans the Studio tree for markdown files containing:

- `slug: __SLUG__`

It generates deterministic slugs in dry-run mode by default, and writes replacements only when `--write` is passed.

## Public Integration API

`workbench.interop` is the only supported external Python API.

External scripts must import from:

```python
from workbench.interop import Document
```

Available symbols:

- `Document`

The `framing` namespace is internal and may change without notice.

## Transport Rules

- Markdown input/output represents exactly one document.
- NDJSON is required for multi-record streaming.
- Multi-document markdown streams are not supported.

## Record Envelope Boundary

Workbench is an NDJSON consumer and Markdown writer.

Workbench reads only these record envelope fields when writing files:

- `content`
- `batch_slug`
- `slug` (required for `write-back`)
- `filename_hint` (optional for `write-new`)
- `provenance` (optional for `write-new`)

All other record fields are ignored by the writer commands.

Workbench is not responsible for:

- schema definition
- record interpretation
- multimodal input handling
- analysis orchestration

Those responsibilities belong to AutoScribe workers.

Batch slugs are treated as opaque execution identifiers.

Layer responsibilities:

| Layer | Responsibility |
| --- | --- |
| Providers / AutoScribe | Produce and transform NDJSON records |
| `wkb stream` | Extract `content` from NDJSON records and emit concatenated bare markdown in record order |
| `wkb scan-sentinel` | Select markdown files whose first line contains a valid ASC batch sentinel and emit path NDJSON rows |
| `wkb compile-assets` | Compile fully-qualified URI links into managed frontmatter `sources`/`assets` and remove inline source links |
| `wkb write-new` / `wkb write-back` | Consume NDJSON records and persist markdown files |
| `wkb write-stream` | Pass markdown through unchanged |
| `wkb create-vault` | Initialize new/existing folders as vaults using `_vault_registry`, template install, and `_common` symlink |

## Pandoc Integration Policy

Workbench does **not** own Pandoc filters/templates internally.

- Pandoc assets and filter logic live in the standalone `tls` package under `~/Tools`.
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

Use explicit data-dir wiring when needed:

```bash
pandoc "$INPUT.md" \
  --data-dir "$HOME/.local/share/pandoc" \
  --template default \
  --lua-filter "$HOME/.local/share/pandoc/filters/lua/content-filtering/filter_components.lua" \
  -o "$OUTPUT.pdf"
```

Optional shell helper:

```bash
wb-pandoc() {
  pandoc --data-dir "$HOME/.local/share/pandoc" "$@"
}
```

## Ownership Boundaries

- In scope: CLI orchestration, stream flows, shell lifecycle, and vault logic.
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

## Architectural Boundary Rule

Workbench must never import from the Autoscribe engine (`asc.*`).

The only contract between Workbench and Autoscribe is the NDJSON stream over stdout/stdin.

No shared Python modules.
No shared IO layers.
No cross-imports.
