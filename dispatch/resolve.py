WORK ORDER

Purpose
Resolve an ordered JSON slug selection into ordered absolute filepaths for Pandoc.
This is the first stage of the ingest chain.
It must also create the pre-ingest git receipt tag before emitting any paths.

Scope
- Input: JSON file containing an ordered list of unique content slugs.
- Output: stdout = newline-delimited absolute filepaths only, in the same order.
- Side effect: create annotated git tag recording the submission receipt.
- This command runs only from inside a valid vault root / subdir and only inside a valid repo.

Required dependencies
- Use rg_search for slug -> filepath resolution.
- Use the repo package for all git/repository operations.
- Use existing vault discovery helpers for current registered vault root.
- Use pathlib throughout.

Non-goals
- Do not parse markdown.
- Do not validate markdown structure.
- Do not emit NDJSON.
- Do not carry selection_id through the pipe.
- Do not inspect instruction/profile files.
- Do not create directories or repair the repo.
- Do not shell out directly to git from this module.

Contract
- Preserve input order exactly.
- Hard-fail on duplicate slugs.
- Hard-fail if any slug cannot be resolved to exactly one filepath.
- Hard-fail if any resolved path does not exist or is not a regular file.
- Hard-fail if any resolved path is outside the current registered vault.
- Hard-fail if repo is unavailable.
- For now, hard-fail if repo is dirty unless the repo package already exposes a single snapshot/pre-submit helper. Do not invent ad hoc git subprocess calls here.

Resolver contract
- Slug resolution must go through rg_search, not through local regex walking or manual scans.
- rg_search is the sole authority for slug -> filepath lookup.
- This command should consume a helper exposed by rg_search, not reimplement search logic inline.
- Hard-fail unless each slug resolves to exactly one filepath.

Receipt tag
Create one annotated submit tag before writing any paths to stdout.

Tag name
- submit/<receipt_id>

receipt_id
- any compact unique id is fine
- include it only in the tag name/message
- it does NOT need to travel through the pipe

Tag target
- current snapshot commit
- if dirty-state handling is supported centrally in repo, use that helper
- otherwise refuse dirty repo

Tag message: store
- receipt_id
- created_at
- cwd
- vault_root
- commit
- record_count
- ordered slugs
- ordered absolute filepaths
- manifest/source json path
- optional manifest hash if cheap and already available

stdout
Emit only:
<abs_path_1>
<abs_path_2>
...

No JSON, no logging, no tag name, no status text on stdout.

stderr
Allowed for brief human diagnostics only.
Keep machine-readable output off stderr for now.

Suggested helpers
- load_selection_json(path) -> list[str]
- validate_unique_ordered_slugs(slugs) -> list[str]
- resolve_slug_to_filepath(slug, vault_root) -> Path
- ensure_regular_file(path) -> None
- ensure_within_vault(path, vault_root) -> None
- create_submit_receipt(...) -> str
- emit_paths(paths) -> None

Expected helper sources
- rg_search: resolve_slug_to_filepath / equivalent central slug lookup helper
- repo: repo discovery, dirty check, current commit lookup, annotated tag creation
- vault helpers: discover current registered vault root

Validation rules
For each slug:
1. resolve slug to filepath via rg_search
2. confirm filepath is absolute
3. confirm filepath exists
4. confirm filepath is a regular file
5. confirm filepath is inside current vault root

Do not parse frontmatter or markdown here.
Slug correctness is delegated to rg_search; markdown validity is delegated to Pandoc.

Implementation notes
- Keep receipt creation separate from path emission so failures happen before partial stdout.
- The repo package is the only boundary for git logic in this module.
- rg_search is the only boundary for slug lookup in this module.
- This file should remain a thin orchestration layer over those two packages.

Pseudo-flow
1. discover current registered vault root
2. ensure repo exists for that vault via repo package
3. read selection json
4. extract ordered slug list
5. reject duplicates / empty selection
6. resolve every slug to exactly one filepath via rg_search
7. verify every resolved path exists, is absolute, is a regular file, and sits within the vault
8. obtain snapshot commit or refuse dirty repo via repo package
9. create annotated submit/<receipt_id> tag with full ordered manifest via repo package
10. print ordered absolute filepaths to stdout, one per line
11. exit 0

Failure policy
On any failure:
- emit nothing to stdout
- create no submit tag
- raise with a clear message

Rationale
This stage is the authoring-side boundary ledger.
It records exactly what was submitted, while keeping the pipe payload as plain filepaths for Pandoc.
Markdown validity is checked downstream by Pandoc, not here.
Slug lookup and git behavior are delegated to rg_search and repo respectively, to avoid duplicated logic.