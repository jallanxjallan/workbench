```text
WORK ORDER: PROFILE UPLOAD AS WHOLE-SET REFRESH
==============================================

GOAL
----
Profiles change infrequently, so do not bother with package-style reference discovery.

Instead:

    wkb upload-profiles

always scans the full authored profile set, reads every profile YAML file, hashes each file,
builds NDJSON records, and sends the whole set to `asc upload`.

`asc upload` remains generic:
- map slug -> ULID
- compare stored hash
- skip unchanged records
- write changed/new records directly

Profiles are plain YAML files, not markdown notes.

--------------------------------------------------------------------------------
OPERATOR FLOW
--------------------------------------------------------------------------------

1. Operator runs:

       wkb upload-profiles

2. Workbench:
   - scans profile roots for `*.yaml` / `*.yml`
   - reads each profile file
   - extracts slug from YAML
   - hashes full file content
   - emits one NDJSON record per profile

3. AutoScribe:
   - upserts each profile record by slug/ULID/hash

No per-profile selection logic.
No package linkage.
No special handler.

--------------------------------------------------------------------------------
PSEUDOCODE: CLI ENTRY
--------------------------------------------------------------------------------

function cli_upload_profiles():
    result = upload_all_profiles()
    print_human_summary(
        found=result.found,
        uploaded=result.uploaded,
        skipped=result.skipped,
        invalid=result.invalid_count,
    )


--------------------------------------------------------------------------------
PSEUDOCODE: `upload_all_profiles()`
--------------------------------------------------------------------------------

function upload_all_profiles():
    profile_paths = discover_profile_files()

    records = []
    invalid = []
    seen_slugs = {}

    for path in profile_paths:
        file_text = read_text(path)

        try:
            profile_data = parse_yaml(file_text)
        except Exception as exc:
            invalid.append({
                "path": path,
                "error": "yaml_parse_failed",
                "detail": str(exc),
            })
            continue

        slug = profile_data.get("slug")
        if not slug:
            invalid.append({
                "path": path,
                "error": "missing_slug",
            })
            continue

        if slug in seen_slugs:
            invalid.append({
                "path": path,
                "error": "duplicate_slug",
                "other_path": seen_slugs[slug],
                "slug": slug,
            })
            continue

        seen_slugs[slug] = path

        file_hash = hash_profile_file(file_text)
        record = build_profile_record(
            slug=slug,
            path=path,
            file_text=file_text,
            file_hash=file_hash,
        )
        records.append(record)

    if invalid is not empty:
        fail_with_validation_errors(invalid)

    upload_result = asc_upload(stream=records, kind="profile")

    return {
        "found": len(records),
        "uploaded": upload_result.uploaded,
        "skipped": upload_result.skipped,
        "invalid_count": len(invalid),
    }


--------------------------------------------------------------------------------
PSEUDOCODE: `discover_profile_files()`
--------------------------------------------------------------------------------

function discover_profile_files():
    roots = profile_search_roots()

    paths = []
    for root in roots:
        paths.extend(sorted(glob(root, "*.yaml")))
        paths.extend(sorted(glob(root, "*.yml")))

    return stable_unique_paths(paths)

NOTES
-----
- Search only the authored profile directories.
- Do not search generated/export directories.
- Deterministic ordering helps reproducibility and testing.

--------------------------------------------------------------------------------
PSEUDOCODE: `hash_profile_file(file_text)`
--------------------------------------------------------------------------------

function hash_profile_file(file_text):
    normalized = normalize_newlines(file_text)
    return sha256(normalized.encode("utf-8")).hexdigest()

NOTES
-----
- Hash the entire YAML file, not extracted fields.
- Any frontmatter/field/order/content change in the source file should produce a new hash.

--------------------------------------------------------------------------------
PSEUDOCODE: `build_profile_record(...)`
--------------------------------------------------------------------------------

function build_profile_record(slug, path, file_text, file_hash):
    return {
        "slug": slug,
        "kind": "profile",
        "hash": file_hash,
        "content": file_text,
        "input_record": {
            "slug": slug,
            "origin": "workbench.upload_profiles",
            "filepath": str(path),
            "filename_hint": basename(path),
        }
    }

NOTES
-----
- Store the raw YAML text in `content`.
- `asc upload` does not need to understand profile structure.
- Structural interpretation happens later, wherever profile content is consumed.

--------------------------------------------------------------------------------
PSEUDOCODE: `asc upload`
--------------------------------------------------------------------------------

function asc_upload(stream, kind=None):
    uploaded = 0
    skipped = 0

    for record in parse_ndjson(stream):
        slug = record["slug"]
        record_kind = record["kind"]
        new_hash = record["hash"]

        ulid = registry_get_or_create_ulid(slug)
        key = storage_key_for(kind=record_kind, ulid=ulid)

        existing = redis_hgetall(key)
        if existing exists:
            existing_hash = existing.get("hash")
            if existing_hash == new_hash:
                skipped += 1
                continue

        payload = dict(record)
        payload["ulid"] = ulid

        redis_hset(key, mapping=payload)
        uploaded += 1

    return {
        "uploaded": uploaded,
        "skipped": skipped,
    }

--------------------------------------------------------------------------------
EXPECTED BEHAVIOR
--------------------------------------------------------------------------------

Case A: all profile files unchanged
    - all records skipped by hash
    - no rewrites

Case B: one profile changed
    - only that record rewritten
    - all others skipped

Case C: new profile added
    - new slug gets ULID
    - record uploaded

Case D: invalid YAML file
    - hard fail before upload

Case E: duplicate slug across two YAML files
    - hard fail before upload

--------------------------------------------------------------------------------
SUGGESTED FUNCTION SHAPES
--------------------------------------------------------------------------------

workbench/cli/upload_profiles.py
    cli_upload_profiles()

workbench/control/upload_profiles.py
    upload_all_profiles()
    discover_profile_files()
    hash_profile_file(file_text)
    build_profile_record(...)

autoscribe/cli/upload.py
    asc_upload(stream, kind=None)

autoscribe/core/upload.py
    registry_get_or_create_ulid(slug)
    storage_key_for(kind, ulid)

--------------------------------------------------------------------------------
GUARDRAILS
--------------------------------------------------------------------------------

1. Upload the full authored profile set every run.
2. Accept only `.yaml` / `.yml` source files.
3. Every file must parse as valid YAML.
4. Every profile must contain a slug.
5. Duplicate slugs are a hard failure.
6. Hash comparison belongs in `asc upload`, not Workbench.
7. `asc upload` must stay generic and record-driven.

--------------------------------------------------------------------------------
MINIMAL TEST MATRIX
--------------------------------------------------------------------------------

1. two valid profile YAML files, both new
   -> 2 uploaded

2. two valid profile YAML files, unchanged
   -> 2 skipped

3. one changed YAML file, one unchanged
   -> 1 uploaded, 1 skipped

4. one invalid YAML file
   -> hard fail, no upload

5. two files with same slug
   -> hard fail, no upload

6. one file missing slug
   -> hard fail, no upload

--------------------------------------------------------------------------------
ONE-LINE SUMMARY
--------------------------------------------------------------------------------

`wkb upload-profiles` always scans and uploads the entire authored YAML profile set, while
`asc upload` generically handles slug-to-ULID mapping, hash comparison, and upsert/skip logic.
```

