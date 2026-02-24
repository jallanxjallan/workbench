# WORK ORDER
## Title: Workbench Pruning — Runtime-Only Toolchain

---

## 🎯 Objective

Convert Workbench into a **pure runtime toolchain repository**.

After this pass, Workbench will contain:

- CLI tools
- Shell integration layer
- Runtime assets (Pandoc, Obsidian support files)
- Minimal packaging metadata

Workbench will NOT contain:

- Documentation folders
- Reference material
- Naming modules
- Test infrastructure
- Experimental fossils
- Backup artifacts
- Architectural notes

All documentation and architecture material will live in:

```
~/Dropbox/references
```

Runtime documentation will exist only as:

- Python docstrings
- --help CLI output
- Inline shell comments

This repo becomes operational infrastructure only.

---

# 🔥 Phase 1 — Remove Documentation Completely

Delete the following directories entirely:

```
docs/
assets/reference/
assets/naming/
```

Delete root-level work order markdown files:

```
setup_w_dynamic_authorized_cli_work_order.md
strip_cli_flags_and_harden_atomic_tools_work_order.md
```

If any architectural or reference content is worth keeping:

→ Move it manually to `~/Dropbox/references`

Workbench must contain zero documentation folders.

---

# 🔥 Phase 2 — Remove Tests and Caches

Delete:

```
dev/tests/
dev/.pytest_cache/
.pytest_cache/
dev/experimental/root_pytest_cache/
```

Add to `.gitignore` if not already present:

```
.pytest_cache/
__pycache__/
*.pyc
```

All tests now live in `~/Tests`.

Workbench is not a testing environment.

---

# 🔥 Phase 3 — Remove Legacy and Experimental Fossils

Delete entirely:

```
dev/legacy_ingest/
dev/experimental/tmp_artifacts/
```

Retain only:

```
dev/experiments/
```

This folder is scratch space only and must not contain runtime logic.

---

# 🔥 Phase 4 — Flatten CLI Structure

Current structure:

```
tools/cli/
```

Move all contents to:

```
cli/
```

Then delete:

```
tools/
```

Workbench should not have redundant nesting.

---

# 🔥 Phase 5 — Remove Adapters Layer

Delete entirely unless actively required:

```
adapters/
```

If anything inside is still needed, move it into `cli/`.

Workbench is not a framework with adapters.

---

# 🔥 Phase 6 — Remove Backups Folder

Delete:

```
backups/
```

Workbench is not a backup host.

---

# 🔥 Phase 7 — Clean Assets Structure

After removing reference and naming folders, assets should contain only runtime dependencies.

Final assets layout should resemble:

```
assets/
  pandoc/
  obsidian/
```

If `assets/templates/` contains runtime-required templates, keep them.
If purely reference material, remove or relocate.

---

# 🔥 Phase 8 — Shell Layer De-duplication

Rename redundant layer names.

Examples:

```
shell/modules/  →  shell/commands/
```

Avoid duplicate naming like:

```
core/core.zsh
env/core.zsh
```

Rename clearly:

```
core/base.zsh
env/environment.zsh
```

No repeated semantic labels.

---

# 🔥 Phase 9 — Move Packaging to Root

If located in:

```
dev/packaging/pyproject.toml
```

Move to project root:

```
pyproject.toml
```

Delete:

```
dev/packaging/
```

---

# 🧼 Expected Final Structure (Conceptual)

```
Workbench/
├── cli/
├── shell/
│   ├── core/
│   ├── env/
│   ├── commands/
│   └── aliases.zsh
├── assets/
│   ├── pandoc/
│   └── obsidian/
├── dev/
│   └── experiments/
├── pyproject.toml
├── .pre-commit-config.yaml
├── .github/
└── .gitignore
```

No docs.
No reference.
No tests.
No backups.
No architectural essays.

---

# 📌 Commit Strategy

Commit in controlled steps:

1. REWRITE: remove docs and reference material
2. REWRITE: remove tests and caches
3. REWRITE: remove legacy ingest and fossils
4. REWRITE: flatten cli structure
5. REWRITE: remove adapters and backups
6. STYLE: rename shell layer duplicates

Do not batch into a single commit.

---

# 🧠 Architectural Rule After This Pass

Workbench is now:

A hardened runtime toolchain.

All thinking happens elsewhere.
All documentation lives elsewhere.
All experimentation happens elsewhere.

This repository executes.
Nothing more.

