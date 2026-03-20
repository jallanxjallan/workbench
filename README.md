# Workbench

Workbench is a stateless CLI layer.

It:
- reads git
- emits NDJSON
- transforms records

It does not:
- orchestrate workflows
- manage state
- execute pipelines

Shell composition is the execution model.

## Architecture

Core boundary:

- `Git` = intent, primarily annotated `batch/<id>` tags
- `NDJSON` = transport, with one canonical record shape
- `asc` = execution and ledgering
- `Workbench` = deterministic CLI primitives
- `Obsidian` = authoring only

Workbench never imports Autoscribe modules. Integration is stdin/stdout NDJSON only.

## Canonical Record Contract

Every ingest-facing command accepts or emits this exact shape:

```json
{"content":"...","input_record":{...}}
```

Rules:

- `content` must always exist and must be a string.
- `input_record` must always exist and must be an object.
- `input_record` may be extended, but not removed.
- No additional top-level fields are allowed.
- Invalid JSON or schema drift is a hard failure.

The record helpers live in [workbench/ingest/records.py](/home/jeremy/Workbench/workbench/ingest/records.py).

## Batch Model

Canonical source of batch truth:

- annotated git tag `batch/<id>`

Canonical tag payload:

```yaml
batch: <id>
description: <optional human-readable text>
order:
  - <slug>
  - <slug>
```

Batch ids are treated as opaque strings by Workbench. The target operator format is `YYYYMMDD-HHMMSS-xxxx`, but runtime code does not semantically parse the id.

## Primary Commands

Entry point:

```bash
wkb
```

Batch and NDJSON primitives:

- `wkb batch-slugs <id>`
- `wkb slugs-to-files`
- `wkb show-batch <id>`
- `wkb validate-batch <id>`
- `wkb ingest-batch <id>`: compatibility emitter for batch slug records
- `wkb confirm inflight <id>`

Control and publishing commands:

- `wkb compile-registries`
- `wkb compile-regex`
- `wkb compile-control`
- `wkb compile-assets`
- `wkb publish-control`
- `wkb publish-context`
- `wkb stream`

Vault-authoring support commands:

- `wkb writevault [--overwrite] [--folder <path>] [--template <name>]`
- `wkb writestream`
- `wkb create-vault <vault-name-or-path>`
- `wkb vault template apply --template <template_name> --files file1.md file2.md`

## Composition Model

Workbench commands are designed to compose in the shell:

```bash
wkb batch-slugs <id> | wkb slugs-to-files
```

Pandoc and ingest execution stay outside Workbench:

```bash
wkb batch-slugs <id> \
  | wkb slugs-to-files \
  | <external markdown-to-ndjson step> \
  | asc ingest --stdin
```

Workbench does not internally chain these steps for you.

## Repository Layout

Runtime and source roots:

- `workbench/`: Python package for CLI, batch parsing, ingest helpers, control compilation, writing, and runtime utilities
- `_compiled/control/`: compiled control artifacts
- `_compiled/registries/`: compiled registry outputs
- `_compiled/regex/`: compiled regex outputs
- `tools/pandoc/`: bundled tooling support, including Pandoc defaults and filters
- `obsidian/`: authoring-side shared assets and templates

Control plane:

- `~/Control`: authoritative YAML/control repository
- `~/Control/Registry/`: registry YAML
- `~/Control/Regex/definitions/`: regex YAML definitions

Workbench reads compiled JSON artifacts from `_compiled/`. The Control repo stores the authoritative YAML sources used to build them.

## Boundaries

Workbench batch commands:

- may read git tags
- may read tracked markdown files
- may emit NDJSON to stdout

Workbench control logic:

- compiles and publishes control/context artifacts
- should remain pure logic at the control layer

Obsidian:

- is an authoring layer
- may contain incomplete or pre-template notes
- is not the source of ingest truth

Frontmatter is a vault-side concern. Slugs are only required when a note is selected into a batch or otherwise resolved by slug-aware commands.

## Notes

To migrate existing vault files from `batch_id:` to `batch:`, run:

```bash
tools/migrate_batch_field.zsh <vault-root>
```

Then verify:

```bash
rg '^batch:' <vault-root>
```
