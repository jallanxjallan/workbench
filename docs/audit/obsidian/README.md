# Obsidian Integration Audit

## 1. Executive Summary

### What Works
- The repo has a clear shared-vault layer: `_common` docs, templates, queries, and macros under `obsidian/common`.
- Live batch commands are now stateless NDJSON emitters built around annotated `batch/<id>` tags.
- Live ingest-adjacent code remains read-only with respect to authored notes.
- Vault provisioning, templating, and `_ingest` writing are separated from ingest execution.
- Frontmatter parsing is strict rather than silently permissive.

### What Is Broken
- The named batch surfaces still do not line up end-to-end:
  - Obsidian macros create ordered git commits.
  - Active Workbench batch commands resolve annotated `batch/<id>` tags.
- Batch id formatting disagrees between the macro/docs and the parser.
- Obsidian-side docs and queries still describe pre-rationalization behavior in places.
- There is still no committed shell-level bridge from vault selection to batch tag creation.

### What Is Risky
- Shared docs and queries overstate slug requiredness and mislabel valid pre-template notes as failures.
- Frontmatter still crosses the Pandoc normalization boundary as provenance, despite the desired “vault-side only” model.
- Silent fallbacks in the DataviewJS selector can change candidate sets without blocking the user.
- Live template application can rewrite identity metadata by introducing `legacy_slug`.

## 2. Top 5 Issues

1. Batch signaling is split across incompatible mechanisms.
   - Obsidian macros serialize commits; Workbench resolves annotated tags.

2. Batch id format is inconsistent.
   - Macro/docs use `YYYYMMDD-HHMM`; the current Workbench target format is `YYYYMMDD-HHMMSS-xxxx`.

3. Obsidian-facing docs still reference batch behavior that no longer exists in Workbench.
   - `wkb compile-batch` and `select-records` are gone; the live primitives are `batch-slugs`, `slugs-to-files`, `show-batch`, and `validate-batch`.

4. Slugless pre-template notes are treated as broken by shared docs/queries.
   - This conflicts directly with the current lifecycle truth.

5. Frontmatter is not fully contained to the vault.
   - Active Pandoc filters move metadata into NDJSON provenance.

## 3. Immediate Actions (Next Work Orders)

- Unify the batch contract.
  - Pick one canonical source of batch truth: commit message or annotated tag.

- Unify the batch id format.
  - Make macros, docs, parsers, and any bridge tooling accept the same shape.

- Add the missing shell bridge.
  - Batch selection in the vault still needs an explicit path to create annotated `batch/<id>` tags.

- Rewrite slug-related docs and integrity queries by lifecycle stage.
  - Separate “pre-template valid” from “ready-for-batch required”.

- Define a strict metadata boundary for NDJSON.
  - Decide what frontmatter, if any, may cross into provenance.

## 4. Safe-To-Ignore Items

- Archived `_archive` docs and scripts are safe to leave in place as long as they stay clearly deprecated and are not linked from active workflows.
- Vendored `.obsidian/plugins/*` assets are provisioning artifacts, not the source of note-format policy.
- Strict YAML parse failures are not a bug in this audit; they are one of the healthier guardrails currently present.

## 5. Verification Pass

Static searches run:
- `slug`
- `frontmatter`
- `yaml`
- `metadata`
- `write`
- `overwrite`

Verification results:
- No hidden authored-note mutation was found in the active ingest path.
  - `workbench/cli/batch_slugs.py` and `workbench/cli/slugs_to_files.py` read tags and files, then emit NDJSON only.
  - `tools/pandoc/filters/lua/output/emit_ndjson.lua` emits NDJSON and stderr diagnostics, but does not write vault notes.

- Active mutation surfaces are separate and explicit.
  - `workbench/cli/vault_template.py` rewrites notes.
  - `workbench/lib/vault_writer.py` writes new files only into `_ingest/`.
  - `workbench/cli/create_vault.py` provisions vault structure.

- Silent or semi-silent fallbacks do exist.
  - DataviewJS selector falls back from TOC resolution to filesystem scan.
  - `emit_ndjson.lua` silently prunes empty metadata structures.
  - `writevault` skips invalid or slugged records and logs warnings instead of hard-failing.

## 6. Output Map

- `docs/audit/obsidian/components.md`
- `docs/audit/obsidian/assumptions.md`
- `docs/audit/obsidian/mismatches.md`
- `docs/audit/obsidian/system_role.md`
- `docs/audit/obsidian/risks.md`
