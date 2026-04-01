# AGENTS.md

Guidance for Codex and other coding agents working in this repository.

## Purpose

Workbench is the operator-facing orchestration layer in the wider Workspace system.  
Its job is to provide clean CLI and file-system tooling around a contract-first pipeline.

The main architectural rule is simple:

- **transport** handles interop and record movement
- **repo** handles all Git interactions
- **scan** handles filesystem indexing and entity discovery

If you are about to write code that talks to the outside world, queries Git, or walks the filesystem, stop and check those packages first.

---

## Non-negotiable package boundaries

### 1. Use `transport` for all interop communications

Use the `transport` package for things like:

- NDJSON streaming
- record iteration
- serialization / deserialization
- piping data between commands
- file/stream adapters used to move records across script boundaries

Do **not** scatter these concerns across the codebase with ad hoc:

- `json.loads(...)` / `json.dumps(...)`
- hand-rolled NDJSON readers
- repeated `_iterjson` helpers
- one-off stdin/stdout parsing

If the code is moving structured records between components, it belongs in `transport`.

---

### 2. Use `repo` for all Git calls

Use the `repo` package for **every** Git operation.

This includes:

- repo discovery
- dirty checks
- tracked/untracked status
- commit queries
- tag queries
- snapshot logic
- any future object/ref inspection

Do **not**:

- call `git` directly from unrelated modules
- shell out with `subprocess.run(["git", ...])` outside `repo`
- duplicate Git logic in CLI scripts or helpers

Git is an operational dependency in this project, not a casual shell command.  
Treat `repo` as the single authority.

---

### 3. Use `scan` for all filesystem indexing and entity discovery

Use the `scan` package for:

- slug → filepath resolution
- filesystem indexing
- ripgrep-backed discovery
- locating candidate files
- entity lookup by prefix, class, slug, or other indexed metadata

Do **not**:

- re-walk trees with ad hoc `Path.rglob()` when the task is discovery/indexing
- duplicate slug resolution logic
- bury entity-finding code inside unrelated modules
- invent secondary indexing helpers unless they genuinely belong inside `scan`

If the question is “where is the thing?” or “which files match these rules?”, the answer should usually start in `scan`.

---

## Preferred design style

### Keep CLI entrypoints thin

CLI scripts should mostly do three things:

1. parse args
2. call domain helpers
3. emit results

Do not bury business logic in `if __name__ == "__main__"` blocks.

---

### Prefer composition over local cleverness

Before writing new helpers, check whether the behavior belongs in:

- `transport`
- `repo`
- `scan`

A small number of strong packages is preferred to many one-off utilities.

---

### Do not bypass package boundaries for convenience

Even if a direct `subprocess`, `json`, or `Path.rglob()` call feels faster, do not do it if the concern already belongs to one of the core packages.

The short-term shortcut becomes long-term duplication.

---

### Prefer `pathlib`

Use `pathlib.Path` for internal path handling.

- Convert to absolute paths before handing paths to external processes
- Avoid stringly-typed path manipulation where a `Path` object is clearer
- Do not use `os.path` unless there is a compelling technical reason

---

### Fail clearly, not magically

Prefer explicit failure to silent filesystem mutation.

In general:

- do not auto-create directories unless that is the explicit contract
- do not silently repair invalid state
- do not swallow exceptions that indicate contract drift
- do not “help” by guessing when the schema or location should be authoritative

An operation that should fail loudly is better than one that quietly corrupts workflow assumptions.

---

## Existing project assumptions

### NDJSON is the main interop contract

Workbench is built around structured record flow.

Assume that:

- streams matter
- record shape matters
- script boundaries should remain clean
- stdin/stdout contracts are preferred where practical

When adding or refactoring code, preserve NDJSON-based composition.

---

### Frontmatter and content have different responsibilities

Where markdown files are involved:

- frontmatter is structural / authoring metadata
- content is content
- writeback must preserve frontmatter unless the contract explicitly says otherwise

Do not casually rewrite frontmatter in sinks that are only supposed to replace content.

---

### Slug resolution should be centralized

If code needs to find a document from a slug:

- use `scan`
- do not reimplement slug matching inline
- do not create alternate slug-resolution paths in unrelated modules

There should be one clear route from identity to file location.

---

### Git state is authoritative for document workflow

Dirty checks, snapshot logic, commit ancestry, and similar state belong to `repo`.

Do not recreate “lightweight Git status” with filesystem heuristics.

---

## Refactoring guidance

### Good refactors

- moving repeated NDJSON handling into `transport`
- moving Git subprocess code into `repo`
- moving discovery code into `scan`
- reducing script files to orchestration only
- replacing duplicated helpers with package calls
- tightening contracts and naming

### Bad refactors

- adding compatibility wrappers just to preserve old call shapes during active rework
- introducing generic `utils.py` dumping grounds
- spreading one concern across multiple domains
- hiding important failures behind permissive fallbacks
- replacing explicit contracts with “smart” guessing

---

## Naming guidance

Prefer names that reflect domain responsibility.

Good signs:

- the module name tells you what kind of authority it has
- the function name tells you whether it resolves, scans, emits, writes, reads, or tags
- the caller does not need to know implementation trivia

Avoid vague names like:

- `helpers`
- `common`
- `misc`
- `utils`
- `manager`

unless the file truly is a stable, well-bounded abstraction.

---

## When imports or names are in flux

This repository is under active refactor.  
If names are moving:

- prefer aligning code to the emerging package boundaries
- prefer updating callers to the right abstraction
- avoid adding temporary shims unless explicitly requested
- do not preserve a bad structure just because it existed first

When in doubt, strengthen the architecture instead of preserving drift.

---

## Changes to avoid unless explicitly requested

Do not:

- rewrite broad swaths of unrelated code
- change CLI UX gratuitously
- add extra flags where positional or piped contracts are already clear
- redesign file formats unprompted
- introduce hidden background behavior
- add new dependencies for trivial tasks

Stay narrow. Keep the patch legible.

---

## What a good patch looks like here

A good patch in this repo usually:

- makes boundaries clearer
- removes duplication
- strengthens one authority per concern
- preserves stream-friendly composition
- keeps the operator in control
- leaves fewer surprises for future manual maintenance

---

## Practical rule of thumb

Before writing code, ask:

- Is this interop? → use `transport`
- Is this Git? → use `repo`
- Is this discovery/indexing/resolution? → use `scan`

If the answer is yes and you are not using that package, you are probably in the wrong place.

---

## Final note

Be conservative, explicit, and kind to the future maintainer.

This codebase is being actively shaped into a cleaner architecture.  
Help by reinforcing boundaries, not by improvising around them.