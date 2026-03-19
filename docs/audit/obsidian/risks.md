# Obsidian Integration Risks

## R01
Risk:
- Macro-generated batch ids may not parse in Workbench batch parsers.
Trigger:
- Obsidian batch macros emit `YYYYMMDD-HHMM`, while `workbench/control/batch.py` expects six digits after the hyphen.
Impact:
- Commit-derived batch parsing fails; downstream tooling rejects otherwise valid-looking batch signals.
Likelihood:
- high
Mitigation (future, not now):
- Unify on one batch id format and enforce it in both docs and code.

## R02
Risk:
- Commit-based batch signaling and tag-based ingest are disconnected.
Trigger:
- User relies on Obsidian macros that only create commits, while ingest code expects annotated `batch/<id>` tags.
Impact:
- Batch appears “created” in Obsidian but cannot be ingested by the active Python path.
Likelihood:
- high
Mitigation (future, not now):
- Choose one canonical batch surface or add an explicit bridge from commit to annotated tag.

## R03
Risk:
- `wkb compile-batch` does not run the repo-local compile orchestrator that its name suggests.
Trigger:
- Operator invokes `wkb compile-batch`.
Impact:
- Operational confusion, wrong mental model, and missed validation expectations.
Likelihood:
- high
Mitigation (future, not now):
- Either wire the CLI to `workbench.control.compile_batch` or rename/deprecate the alias.

## R04
Risk:
- `workbench.control.compile_batch` may be internally incompatible with the active Pandoc defaults.
Trigger:
- Repo-local compile path is executed against `external_ingest.yaml`.
Impact:
- Compile fails because expected `batch_slug` is not produced by the visible active filters.
Likelihood:
- medium
Mitigation (future, not now):
- Add an explicit contract test between `compile_batch.py` and `external_ingest.yaml`.

## R05
Risk:
- Valid pre-template notes are mislabeled as broken.
Trigger:
- Operators rely on shared docs or queries that equate missing slug with missing frontmatter.
Impact:
- False positives, incorrect cleanup work, and pressure to add slug too early.
Likelihood:
- high
Mitigation (future, not now):
- Split lifecycle states explicitly in queries and documentation.

## R06
Risk:
- Silent TOC fallback changes the candidate set for batch operations.
Trigger:
- `index_note` is missing, ambiguous, or lacks heading+wikilink structure.
Impact:
- UI silently switches from curated TOC order to filesystem scan; user may batch the wrong notes.
Likelihood:
- medium
Mitigation (future, not now):
- Make fallback explicit and optionally blocking.

## R07
Risk:
- Duplicate or missing slugs stop batch resolution entirely.
Trigger:
- Two markdown files share a slug, or one listed slug resolves to zero files.
Impact:
- Batch compile/ingest aborts.
Likelihood:
- medium
Mitigation (future, not now):
- Enforce slug uniqueness earlier and expose duplicate checks in preflight tooling.

## R08
Risk:
- Template application can alter note identity unexpectedly.
Trigger:
- `wkb vault template apply` encounters a target note with an existing slug and a template containing `slug`.
Impact:
- Existing `slug` is converted to `legacy_slug`; note identity changes without a dedicated identity-migration workflow.
Likelihood:
- medium
Mitigation (future, not now):
- Require explicit confirmation or dedicated migration mode for slug-affecting template application.

## R09
Risk:
- `_ingest` writer silently skips records that include slug.
Trigger:
- NDJSON producer sends `input_record.slug`.
Impact:
- Records never appear in `_ingest/`; operator may only notice via logs.
Likelihood:
- medium
Mitigation (future, not now):
- Promote skip reasons to stdout/stderr summaries or fail fast in strict mode.

## R10
Risk:
- Empty metadata is silently pruned during NDJSON emission.
Trigger:
- Frontmatter fields are present but blank.
Impact:
- Downstream consumers cannot distinguish “blank” from “missing”.
Likelihood:
- medium
Mitigation (future, not now):
- Decide explicitly which fields may be dropped and preserve the rest verbatim.

## R11
Risk:
- Operators assume frontmatter never leaves the vault.
Trigger:
- Pandoc ingest is treated as frontmatter-blind.
Impact:
- Sensitive or purely editorial metadata may still be propagated in provenance payloads.
Likelihood:
- medium
Mitigation (future, not now):
- Define and enforce an allowlist for metadata passed into NDJSON provenance.

## R12
Risk:
- Legacy archived scripts get revived accidentally.
Trigger:
- User runs old QuickAdd/Templater/Panflute helpers from `_archive`.
Impact:
- Direct slug generation, frontmatter rewrite, or note writeback re-enters the live system.
Likelihood:
- low
Mitigation (future, not now):
- Add explicit deprecation banners or move executable legacy assets farther from live shared paths.

## R13
Risk:
- The `State` filter in the DataviewJS selector implies behavior that does not exist.
Trigger:
- User tries to filter by state in `compile_batch_query.js`.
Impact:
- False confidence in filtering results.
Likelihood:
- medium
Mitigation (future, not now):
- Populate state or remove the filter.

## R14
Risk:
- Invalid YAML frontmatter blocks all slug resolution and control compilation.
Trigger:
- Any tracked markdown file in the relevant search set contains broken YAML frontmatter.
Impact:
- Batch resolution, template application, control compile, or publish fails hard.
Likelihood:
- medium
Mitigation (future, not now):
- Add dedicated frontmatter lint/preflight commands for vault repos.

## R15
Risk:
- Vault provisioning assumptions may fail for hand-made or older vaults.
Trigger:
- Vault lacks `_common` symlink, `.obsidian`, or `_vault_registry.json`.
Impact:
- Template apply and writevault discovery fail even if the vault is otherwise usable in Obsidian.
Likelihood:
- medium
Mitigation (future, not now):
- Add a non-destructive repair/diagnostic command for vault structure.
