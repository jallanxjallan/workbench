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
- `~/Control`: pipeline behavior source repository (`verbs/`, `instructions/global/`, `regex/`, `registries/`, `pipeline/`).
- `registries/` and `regex/definitions/` under `Workbench` are legacy fallback roots only.
- `_compiled/control/`: compiled control artifacts (`verbs.json`, `global_instructions.json`, `regex.json`).
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

- `wkb commit <TYPE> <BATCH_SLUG>`
- `wkb compile-registries`
- `wkb compile-regex`
- `wkb compile-control`
- `wkb compile-assets`
- `wkb find-duplicates`
- `wkb generate-slugs [--write]`
- `wkb publish-control`
- `wkb publish-context`
- `wkb stream`
- `wkb writevault [--overwrite] [--folder <path>] [--template <name>]`
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

`wkb writevault` accepts NDJSON records with required `content` and `input_record`, plus optional `slug`, `batch`, `filename_hint`, and `folder`.

To migrate existing vault files from `batch_id:` to `batch:`, run `tools/migrate_batch_field.zsh <vault-root>` and verify the updated keys with `rg '^batch:' <vault-root>`.

## Registry and Regex Compilation

Compile registries:

```bash
wkb compile-registries
```

Compile regex definitions:

```bash
wkb compile-regex
```

Compile external control behavior:

```bash
wkb compile-control
```

Publish compiled global instructions:

```bash
wkb publish-control
```

Only `_compiled/registries`, `_compiled/regex`, and `_compiled/control` contain compiled artifacts.
