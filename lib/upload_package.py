```text
WORK ORDER: MODIFY `wkb upload-package` / `wkb upload-instructions` TO UPLOAD ONLY REFERENCED INSTRUCTIONS
===============================================================================================

GOAL
----
Change the instruction upload flow so that instructions are no longer uploaded as an independent
bulk registry operation. Instead, instructions are upserted only when referenced by a package.

Operator flow becomes:

    wkb upload-package path/to/packages.json

and inside that command:

    upload_package(...) calls upload_instructions(package_json)

where `upload_instructions` receives the already-loaded package JSON object (not a separate path).

DESIGN INTENT
-------------
1. Packages are the only authoritative source of which instructions matter.
2. `upload_instructions` extracts referenced instruction slugs from package definitions.
3. For each referenced slug:
   - resolve the current source file from the vault via ripgrep
   - read the file
   - hash the file bytes/content
   - emit NDJSON record containing slug, hash, raw content, and source metadata
4. `asc upload` should remain generic:
   - map slug -> ULID
   - check whether an existing record with same slug/hash already exists
   - skip if unchanged
   - otherwise write the NDJSON payload directly into Redis / storage
5. No instruction-type-specific upload handler should be required in `asc upload`.

-----------------------------------------------------------------------------------------------
PSEUDOCODE: `wkb upload-package`
-----------------------------------------------------------------------------------------------

function cli_upload_package(package_json_path):
    package_doc = read_json_or_markdown_payload(package_json_path)

    # Step 1: upload referenced instructions first
    instruction_result = upload_instructions_from_package_doc(package_doc)

    # Step 2: upload packages themselves
    package_records = build_package_ndjson(package_doc)
    asc_upload(stream=package_records, kind="package")

    print_human_summary(
        instructions_found=instruction_result.found,
        instructions_uploaded=instruction_result.uploaded,
        instructions_skipped=instruction_result.skipped,
        packages_uploaded=count(package_records),
    )


-----------------------------------------------------------------------------------------------
PSEUDOCODE: `upload_instructions_from_package_doc(package_doc)`
-----------------------------------------------------------------------------------------------

function upload_instructions_from_package_doc(package_doc):
    referenced_slugs = collect_instruction_slugs(package_doc)

    # Only instruction slugs allowed here
    # accepted prefixes: gbl., cxt., spc.
    referenced_slugs = normalize_unique_sorted(referenced_slugs)
    referenced_slugs = [
        slug for slug in referenced_slugs
        if slug startswith "gbl." or slug startswith "cxt." or slug startswith "spc."
    ]

    records = []
    stats = {
        found: 0,
        uploaded: 0,
        skipped: 0,
        missing: [],
        duplicate_matches: [],
    }

    for slug in referenced_slugs:
        matches = resolve_instruction_filepaths_by_slug(slug)

        if matches is empty:
            stats.missing.append(slug)
            continue

        if len(matches) > 1:
            stats.duplicate_matches.append({slug: matches})
            continue

        path = matches[0]
        file_text = read_text(path)
        file_hash = hash_instruction_file(file_text)
        record = build_instruction_record(
            slug=slug,
            path=path,
            file_text=file_text,
            file_hash=file_hash,
        )
        records.append(record)
        stats.found += 1

    if stats.missing is not empty or stats.duplicate_matches is not empty:
        fail_with_resolution_errors(stats)

    results = asc_upload(stream=records, kind="instruction")
    stats.uploaded = results.uploaded
    stats.skipped = results.skipped

    return stats


-----------------------------------------------------------------------------------------------
PSEUDOCODE: `collect_instruction_slugs(package_doc)`
-----------------------------------------------------------------------------------------------

function collect_instruction_slugs(package_doc):
    slugs = []

    # depends on final package shape, but conceptually:
    # package_doc may contain one package or many
    for package in iter_packages(package_doc):
        for step in package.steps:
            # explicit package-level instruction refs
            slugs.extend(step.instructions.gbl or [])
            slugs.extend(step.instructions.cxt or [])
            slugs.extend(step.instructions.spc or [])

            # if your package schema uses a flat refs list instead:
            # for ref in step.instructions:
            #     slugs.append(ref.slug)

    return slugs


-----------------------------------------------------------------------------------------------
PSEUDOCODE: `resolve_instruction_filepaths_by_slug(slug)`
-----------------------------------------------------------------------------------------------

function resolve_instruction_filepaths_by_slug(slug):
    # Use rg against the authored vault(s), not any compiled/export area
    #
    # Match exact frontmatter slug line only.
    # Example rg pattern:
    #   ^slug:\s*<slug>\s*$
    #
    # Restrict to markdown/yaml-bearing note files as appropriate.

    rg_pattern = '^slug:\\s*' + regex_escape(slug) + '\\s*$'

    result = run_rg(
        pattern=rg_pattern,
        roots=instruction_search_roots(),
        glob=['*.md']
    )

    paths = parse_unique_filepaths(result)
    return paths


-----------------------------------------------------------------------------------------------
PSEUDOCODE: `hash_instruction_file(file_text)`
-----------------------------------------------------------------------------------------------

function hash_instruction_file(file_text):
    normalized = normalize_newlines(file_text)
    return sha256(normalized.encode("utf-8")).hexdigest()

NOTES
-----
- Hash the entire source file, not just body content.
- Reason: any change to frontmatter or instruction body should count as a new version candidate.
- Keep normalization minimal and deterministic.

-----------------------------------------------------------------------------------------------
PSEUDOCODE: `build_instruction_record(...)`
-----------------------------------------------------------------------------------------------

function build_instruction_record(slug, path, file_text, file_hash):
    return {
        "slug": slug,
        "kind": "instruction",
        "hash": file_hash,
        "content": file_text,
        "input_record": {
            "slug": slug,
            "origin": "workbench.upload_instructions",
            "filepath": str(path),
            "filename_hint": basename(path),
        }
    }

IMPORTANT
---------
This record should be generic enough that `asc upload` does not need a dedicated
instruction parser/handler. It only needs to:
1. map slug -> ULID
2. determine target key
3. compare existing hash
4. write record as-is if new/changed

-----------------------------------------------------------------------------------------------
PSEUDOCODE: `asc upload`
-----------------------------------------------------------------------------------------------

function asc_upload(stream, kind):
    uploaded = 0
    skipped = 0

    for record in parse_ndjson(stream):
        slug = record["slug"]
        new_hash = record["hash"]

        ulid = registry_get_or_create_ulid(slug)

        key = storage_key_for(kind=record["kind"], ulid=ulid)
        existing = redis_hgetall(key)

        if existing exists:
            existing_hash = existing.get("hash")
            if existing_hash == new_hash:
                skipped += 1
                continue

        # direct write, no instruction-specific handler
        payload = dict(record)
        payload["ulid"] = ulid

        redis_hset(key, mapping=payload)
        uploaded += 1

    return {
        "uploaded": uploaded,
        "skipped": skipped,
    }

-----------------------------------------------------------------------------------------------
EXPECTED BEHAVIOR
-----------------------------------------------------------------------------------------------

Case A: package references unchanged instructions
    - `upload_instructions` resolves files
    - hashes match stored versions
    - `asc upload` skips them
    - package upload continues

Case B: package references modified instructions
    - changed file hash detected
    - instruction records rewritten/upserted
    - package upload continues

Case C: package references missing instruction slug
    - fail before package upload
    - operator must fix slug/file mismatch

Case D: slug resolves to multiple files
    - fail before package upload
    - operator must remove ambiguity

-----------------------------------------------------------------------------------------------
SUGGESTED FUNCTION SHAPES
-----------------------------------------------------------------------------------------------

workbench/cli/upload_package.py
    cli_upload_package(package_json_path)

workbench/control/upload_package.py
    upload_package_doc(package_doc)

workbench/control/upload_instructions.py
    upload_instructions_from_package_doc(package_doc)
    collect_instruction_slugs(package_doc)
    resolve_instruction_filepaths_by_slug(slug)
    hash_instruction_file(file_text)
    build_instruction_record(...)

autoscribe/cli/upload.py
    asc_upload(stream, kind=None)

autoscribe/core/upload.py
    upload_records(stream)
    registry_get_or_create_ulid(slug)
    storage_key_for(kind, ulid)

-----------------------------------------------------------------------------------------------
GUARDRAILS
-----------------------------------------------------------------------------------------------

1. `upload_instructions` must only accept slugs actually referenced by package data.
2. Only `gbl.`, `cxt.`, and `spc.` prefixes are eligible.
3. Slug resolution must be exact, not fuzzy.
4. Missing or ambiguous slug matches must hard-fail.
5. Hash comparison must happen in `asc upload`, not in Workbench.
6. `asc upload` must remain record-generic and not branch on instruction subtype.
7. Package upload must not proceed if referenced instruction resolution fails.

-----------------------------------------------------------------------------------------------
MINIMAL TEST MATRIX
-----------------------------------------------------------------------------------------------

1. package references 3 instructions, all exist, all new
   -> 3 uploaded

2. package references 3 instructions, all exist, hashes unchanged
   -> 3 skipped

3. package references duplicated slug in multiple steps
   -> dedup before upload, only 1 lookup and 1 upload attempt

4. package references missing `cxt.*`
   -> hard fail before package upload

5. package references slug with two rg matches
   -> hard fail before package upload

6. package references mix of gbl/cxt/spc
   -> all handled identically by generic record path

7. changed frontmatter only
   -> hash changes, record uploads

-----------------------------------------------------------------------------------------------
ONE-LINE SUMMARY
-----------------------------------------------------------------------------------------------

`wkb upload-package` becomes the sole operator entry point; it extracts referenced instruction
slugs from package JSON, resolves and hashes the current source files, uploads generic NDJSON
instruction records first, and then uploads the package, while `asc upload` stays generic and
only performs slug->ULID mapping, hash comparison, and direct record write.
```
Good. That simplifies the contract.

```text
DESIGN NOTE: PACKAGE / BATCH JSON CONTAINS FILE SLUGS ONLY
=========================================================

PRINCIPLE
---------
The package JSON and batch JSON must contain only file slugs, not embedded file content,
hashes, snapshots, or copied instruction/profile text.

This allows the same package or batch file to be reused after source files are edited.

IMPLICATION
-----------
A package or batch definition is a reusable selection manifest, not a frozen payload.

So at execution time:

- the JSON supplies only the referenced slugs
- Workbench resolves each slug to the current source file
- Workbench reads the current file contents from disk
- Workbench computes the current hash from disk
- Workbench builds fresh NDJSON from the live source files

Therefore:

- tweak source file
- rerun same package or batch JSON
- current source version is what gets uploaded

--------------------------------------------------------------------------------
UPDATED RULES
--------------------------------------------------------------------------------

1. Package JSON stores only references:
   - package slug
   - step definitions
   - referenced instruction slugs
   - referenced content/file slugs as applicable

2. Batch JSON stores only references:
   - batch slug
   - ordered list of file slugs

3. Neither package nor batch JSON should cache:
   - file content
   - instruction body
   - profile YAML body
   - file hash
   - resolved path

4. Path resolution always happens at run time.

5. Hashing always happens from the current source file at run time.

--------------------------------------------------------------------------------
PSEUDOCODE CONSEQUENCE: BATCH / PACKAGE REUSE
--------------------------------------------------------------------------------

function upload_package(package_json_path):
    package_doc = read_json(package_json_path)

    # package_doc contains slugs only
    instruction_records = resolve_and_materialize_instruction_records(package_doc)
    profile_records = resolve_and_materialize_profile_records_if_needed(package_doc)
    package_records = build_package_records_from_package_doc(package_doc)

    asc_upload(instruction_records)
    asc_upload(profile_records)
    asc_upload(package_records)


function ingest_batch(batch_json_path, batch_slug):
    batch_doc = read_json(batch_json_path)

    # batch_doc contains file slugs only
    content_records = []

    for slug in batch_doc.file_slugs:
        path = resolve_current_filepath_from_slug(slug)
        file_text = read_text(path)
        file_hash = sha256(file_text)
        content_records.append(
            build_content_record(
                slug=slug,
                path=path,
                content=file_text,
                hash=file_hash,
            )
        )

    asc_ingest(batch_slug=batch_slug, records=content_records)

--------------------------------------------------------------------------------
EXAMPLE
--------------------------------------------------------------------------------

Suppose package file says:

    steps:
      - verb: rewrite
        instructions:
          gbl: [gbl.editorial-core]
          cxt: [cxt.omaf-tone]
          spc: [spc.chapter-opening-pass]

Later you edit `cxt.omaf-tone.md`.

You do NOT need to edit the package JSON.

When you rerun:

    wkb upload-package omaf-rewrite.json

the flow is:

- read package JSON
- extract `cxt.omaf-tone`
- find current file for that slug
- read latest file contents
- hash latest contents
- upload only if changed

Same logic for batch files that list content slugs.

--------------------------------------------------------------------------------
BENEFIT
--------------------------------------------------------------------------------

This preserves the clean separation:

- JSON manifest = reusable operator selection
- authored source files = authoritative live content
- upload step = materialization of current source state

That is exactly what you want if package and batch manifests are meant to survive source edits.

--------------------------------------------------------------------------------
ONE-LINE ADDITION TO THE WORK ORDER
--------------------------------------------------------------------------------

Batch and package JSON files are slug-only manifests; all path resolution, file reading,
and hash generation must occur at run time from the current authored source files so the
same manifest can be reused after source edits.
```

