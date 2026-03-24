Agreed. The current draft still has two bits of softness you do not want: `load_package_doc` accepts markdown/YAML/document fallbacks instead of JSON-only, and the “read/hash/build record” path is split across `build_instruction_record` plus external resolution instead of being centralized as one slug-to-upload-record compiler.  

Here is the tightened WO on a single screen:

```text
WO: refactor package upload so wkb upload-package is the only public command

Goal
Make `wkb upload-package` the single operator-facing command for package-related uploads. It compiles a live NDJSON stream from current source files, then pipes that stream to `asc upload`.

Architecture
- `wkb upload-package <package-file>` is the only public package upload command
- package files are always JSON
- package manifests contain slugs only, never cached paths, content, or hashes
- instruction source files are resolved live at upload time
- profiles are removed from this path and uploaded separately when added/changed

Source roots
Assume command is run only from inside a valid vault.
Build a combined slug index from:
- current vault
- `~/Guidance`

No other roots for now.

Behavior
1. Discover current vault root from cwd
2. Scan current vault for slug -> filepath
3. Scan `~/Guidance` for slug -> filepath
4. Merge both indexes
5. Hard-fail on duplicate slug keys across either source
6. Load the package JSON file
7. Extract all referenced instruction slugs from the package JSON
8. Deduplicate those slugs
9. Resolve each slug against the merged index
10. Hard-fail on any missing slug
11. Centralize slug -> current file content -> hash -> NDJSON record in one helper
12. Emit NDJSON records for referenced instructions
13. Emit NDJSON record for the package itself
14. Pipe the whole stream to `asc upload`

Rules
- upload-package is a compiler from live JSON + live markdown sources to NDJSON
- do not store resolved paths in package JSON
- do not store file hashes in package JSON
- do not upload unreferenced instructions
- only referenced instructions are included
- profiles are out of scope for this command
- `asc upload` remains generic and dumb:
  - map slug -> ULID
  - compare hash
  - skip or upsert
  - write records as-is

Instruction eligibility
Only collect/upload instruction slugs referenced by the package.
Current instruction prefixes:
- `gbl.`
- `cxt.`
- `spc.`

Do not scan/upload every instruction in the vault or Guidance.

Centralize record compilation
Introduce one helper responsible for the full instruction compile step, for example:

- `compile_slug_record(slug: str, entry: SlugEntry, *, kind: str = "instruction") -> dict[str, Any]`

This helper must:
- read the current file from disk
- normalize newlines
- hash the exact uploaded text
- build the full NDJSON-ready record

Do not spread this across separate “resolve path / read text / hash text / build record” call sites.
The current code already has the pieces, but they are split between `_read_uploaded_text`, `_hash_text`, and `build_instruction_record`; unify that path around one public internal compiler helper. :contentReference[oaicite:2]{index=2} :contentReference[oaicite:3]{index=3}

NDJSON record shape
Instruction records should look like:

{
  "slug": "<instruction-slug>",
  "kind": "instruction",
  "hash": "sha256:<digest>",
  "content": "<full file text>",
  "input_record": {
    "origin": "vault|guidance",
    "filepath": "<absolute filepath>",
    "filename_hint": "<stem>"
  }
}

Package record should use the same general upload contract already expected by `asc upload`.

Implementation targets
Refactor/add functions along these lines:

- `upload_package(package_path: Path) -> int`
- `discover_upload_roots(cwd: Path | None = None) -> tuple[Path, Path]`
- `build_slug_index(root: Path, origin: str) -> dict[str, SlugEntry]`
- `merge_slug_indexes(*indexes: dict[str, SlugEntry]) -> dict[str, SlugEntry]`
- `load_package_json(package_path: Path) -> dict[str, Any]`
- `collect_instruction_slugs(package_json: dict[str, Any]) -> list[str]`
- `compile_slug_record(slug: str, entry: SlugEntry, *, kind: str = "instruction") -> dict[str, Any]`
- `build_package_record(package_json: dict[str, Any], package_path: Path) -> dict[str, Any]`
- `emit_ndjson(records: Iterable[dict]) -> Iterable[str]`
- `stream_to_asc_upload(lines: Iterable[str]) -> int`

Suggested helper type

@dataclass(frozen=True)
class SlugEntry:
    slug: str
    path: Path
    origin: str   # "vault" or "guidance"

Important constraints
- use `scan.rg` for all file discovery and slug scanning
- do not shell out to `rg` directly in this workflow
- any vault/Guidance slug index must be built on top of `scan.rg`, not ad hoc subprocess code
- package loader is JSON-only; remove markdown, YAML, and Document fallbacks
- use pathlib throughout
- all filepaths in records must be absolute resolved paths
- newline normalization for hashing must follow current house behavior
- hash the exact text being uploaded
- duplicate slug match is always a hard fail
- do not silently prefer vault over Guidance or vice versa
- missing slug is a hard fail before any upload begins

Public command surface
Keep:
- `wkb upload-package <package-file>`

Remove or deprecate from operator workflow:
- standalone `upload-instructions` as a public step in this flow

Profiles
Do not include profiles in `upload-package`.
Create or preserve a separate maintenance path, e.g.:
- `wkb upload-profiles`

Profiles are uploaded only when added/modified.

Non-goals
- no markdown package parsing
- no YAML package parsing
- no Document dependency in this workflow
- no caching layer
- no registry of resolved paths
- no package-side stored hashes
- no profile upload integration
- no fallback precedence between vault and Guidance
- no background sync behavior

Verification
1. package JSON references 3 valid instruction slugs across vault and Guidance
   - all 3 resolve
   - all 3 are emitted once
   - package record is emitted after them

2. same instruction slug referenced multiple times in package JSON
   - uploaded once only

3. referenced slug missing from both sources
   - hard fail before upload starts

4. same slug exists in vault and Guidance
   - hard fail on index merge

5. referenced file content changes but slug stays same
   - hash changes
   - new record emitted

6. unreferenced instruction files present in vault/Guidance
   - not emitted

7. package file is not valid JSON
   - hard fail immediately
   - no fallback parsing attempted

Deliverable
A clean refactor where `wkb upload-package` loads JSON only, builds a live combined slug index from the current vault and `~/Guidance`, resolves only referenced instruction slugs, compiles each slug through one centralized slug-to-record helper, emits one NDJSON stream, and hands that stream to `asc upload`.
```

