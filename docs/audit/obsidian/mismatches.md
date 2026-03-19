# Reality Alignment Check

Ground truth used:
- slug exists only after templating
- files without slug are valid pre-template
- NDJSON is source of truth for ingest
- vault is authoring layer only
- frontmatter is vault-side concern only
- Autoscribe is blind to frontmatter

## A01 `_common` shared layer
Status:
- VALID
Notes:
- Current provisioning and documentation agree that `_common` is a shared vault asset.

## A02 `_vault_registry.json` marks a registered vault
Status:
- VALID
Notes:
- This is a Workbench provisioning rule, not an Obsidian note rule, but it matches current tooling.

## A03 Templates under `_common/templates`
Status:
- VALID
Notes:
- Live templating and legacy docs both rely on this layout.

## A04 Templates require frontmatter
Status:
- VALID
Notes:
- This is consistent with the live templating flow.

## A05 `slug`, `project`, and `stage` are universally required
Status:
- INVALID
Notes:
- Pre-template notes without slug are explicitly valid.
- Leaving this statement unqualified encourages operators to treat valid authoring-state notes as broken.

## A06 Blank `slug:` in templates is acceptable
Status:
- VALID
Notes:
- This aligns with the “slug arrives after templating” lifecycle.

## A07 Templating may rewrite notes
Status:
- VALID
Notes:
- This is a real vault-side mutation surface.
- It is safe only when clearly scoped to template application, not ingest.

## A08 Existing slug may become `legacy_slug`
Status:
- DANGEROUS
Notes:
- The behavior is real but undocumented in shared vault docs.
- It changes note identity metadata during templating and may surprise downstream tooling or users.

## A09 Batch macros require already-slugged notes
Status:
- VALID
Notes:
- Valid only for post-template notes.
- Dangerous when interpreted as a universal rule for all vault notes.

## A10 Slug extraction from cache or raw YAML text is sufficient
Status:
- VALID
Notes:
- Good enough for the current macro implementation.
- Still brittle around unusual YAML formatting or non-top-level slug keys.

## A11 Batch id format `YYYYMMDD-HHMM`
Status:
- DANGEROUS
Notes:
- The macro/docs emit a four-digit time suffix.
- `workbench/control/batch.py` parses a six-digit suffix.
- If left unchanged, commit-derived batch parsing will reject macro-generated commit messages.

## A12 A commit alone is a sufficient batch signal
Status:
- DANGEROUS
Notes:
- Obsidian macros emit commits.
- Active ingest/compile code resolves annotated `batch/<id>` tags.
- Current repo shows no live bridge from macro commit to required batch tag.

## A13 Authored content defaults to `contents/`
Status:
- VALID
Notes:
- This is a vault convention and current shared default.

## A14 Silent fallback from TOC to filesystem is acceptable
Status:
- DANGEROUS
Notes:
- The selector does this today.
- It can mask TOC drift and change batch candidates without blocking the user.

## A15 TOC selection depends on headings plus wikilinks
Status:
- VALID
Notes:
- This matches the current DataviewJS parser.

## A16 `class` and `stage` are useful vault-side filters
Status:
- VALID
Notes:
- These are live conventions and remain purely vault-side.

## A17 `state` is a live selection field
Status:
- INVALID
Notes:
- The current selector renders the filter but never populates it.
- Leaving it unchanged makes the UI imply capability that is not present.

## A18 `!slug` means “missing frontmatter”
Status:
- INVALID
Notes:
- A note can have frontmatter and still lack slug.
- A pre-template note without slug is valid by current pipeline truth.

## A19 Every slug resolves to exactly one file
Status:
- VALID
Notes:
- Current batch and control code require this.
- Operationally risky, but the assumption itself matches the live pipeline contract.

## A20 Slugs use conservative lowercase ASCII syntax
Status:
- VALID
Notes:
- Current parsers and docs agree on a restrictive slug shape.

## A21 Invalid YAML is fatal
Status:
- VALID
Notes:
- This is a desirable hard-fail behavior for current tooling.

## A22 `compile_batch.py` can derive `batch_slug` from active Pandoc output
Status:
- DANGEROUS
Notes:
- `external_ingest.yaml` only enables provenance capture plus NDJSON emission.
- Visible filters preserve metadata into `origin`, but they do not visibly synthesize `batch_slug`.
- `compile_batch.py` therefore appears internally inconsistent or orphaned in the current repo snapshot.

## A23 Active ingest is read-only for authored notes
Status:
- VALID
Notes:
- Static verification found no note writeback in `workbench/control/ingest_batch.py` or the active Lua emit chain.

## A24 `_ingest` writer should reject slugged NDJSON records
Status:
- VALID
Notes:
- This matches a strict “raw ingest staging only” policy.
- It becomes risky only if future NDJSON producers legitimately include slugged draft records.

## A25 Frontmatter stays vault-side only
Status:
- INVALID
Notes:
- Current Pandoc filters transport frontmatter-derived metadata into `input_record.origin`.
- Even if Autoscribe ignores it, the normalization layer still carries it through.

## A26 Empty metadata can be pruned silently
Status:
- DANGEROUS
Notes:
- Current filters do this for convenience.
- It removes the distinction between “explicitly blank” and “absent”, which can hide authoring intent.

## A27 Legacy Obsidian scripts may mutate notes and `_ingest/` files directly
Status:
- DEPRECATED
Notes:
- This behavior exists only in `_archive`.
- If reactivated, it would violate current authoring/ingest boundaries.

## A28 Legacy Pandoc may generate slugs and write notes back into vault folders
Status:
- DEPRECATED
Notes:
- The direct-write Panflute branch is not part of the active defaults.
- If revived, it would directly contradict the current NDJSON-first pipeline model.

## Cross-Cutting Mismatches

### Batch Surface Split
Status:
- DANGEROUS
Notes:
- Obsidian macro behavior, commit templates, `select-records`, tag-based ingest, and repo-local compile do not currently form one coherent documented path.
- The codebase currently contains at least two batch concepts:
  - commit-message batches
  - annotated-tag batches

### Compile-Batch CLI Wiring
Status:
- DANGEROUS
Notes:
- `wkb compile-batch` is wired to `workbench.control.ingest_batch.run_and_confirm`.
- The newer `workbench.control.compile_batch.compile_batch` implementation is present but not exposed by the CLI.

### Query Semantics Drift
Status:
- DANGEROUS
Notes:
- `integrity_missing_frontmatter.md` and `integrity_orphans.md` both reduce to `WHERE !slug`.
- This collapses distinct authoring states into one signal and mislabels valid pre-template notes as problems.
