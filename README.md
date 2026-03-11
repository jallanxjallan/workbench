# Workbench

Workbench is the human control surface for writing operations.

## Architecture

- `Studio`: writing vaults only (outside this repository).
- `Workbench`: operational CLI and tooling.
- `Autoscribe`: processing engine.
- `NDJSON`: strict boundary between Workbench and Autoscribe.

Workbench never imports Autoscribe modules. Integration is stdin/stdout NDJSON only.

## Repository Layout

Runtime and source roots:

- `workbench/`: Python package (`cli`, `lib`, `config`, `slug`, `write`, `assets`, `framing`, `interop`).
- `registries/`: source registries (`editorial.yaml`, `pipeline.yaml`, `verbs.yaml`).
- `regex/definitions/`: source regex definitions.
- `_compiled/registries/`: compiled registry JSON outputs.
- `_compiled/regex/`: compiled regex JSON outputs.
- `tools/tls/`: bundled Workbench tooling support.
- `obsidian/common/`, `obsidian/templates/`: support assets only.

## CLI

Entry point:

```bash
wkb
```

Core commands:

- `wkb compile-registries`
- `wkb compile-regex`
- `wkb compile-assets`
- `wkb find-duplicates`
- `wkb generate-slugs [--write]`
- `wkb scan-sentinel [paths...]`
- `wkb stream`
- `wkb writenew [--folder <name>] [--template <name>]`
- `wkb writeback [--studio-root <path>]`
- `wkb writestream`
- `wkb create-vault <vault-name-or-path>`

Vault template command:

- `wkb vault template apply --template <template_name> --files file1.md file2.md`

## Pipeline Discipline

Commands are designed for pipelines:

```bash
rg ... | wkb stream | asc ingest
```

Writers consume NDJSON from stdin and emit diagnostics to stderr.

## Registry and Regex Compilation

Compile registries:

```bash
wkb compile-registries
```

Compile regex definitions:

```bash
wkb compile-regex
```

Only `_compiled/registries` and `_compiled/regex` contain compiled artifacts.
