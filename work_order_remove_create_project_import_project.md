# Work Order — Remove Deprecated `create-project` and `import-project` Commands

## Objective

Fully remove the deprecated Workbench CLI commands:

- `create-project`
- `import-project`

along with any modules, helpers, or assets used **exclusively** by those commands.

The goal is to simplify the Workbench CLI surface and eliminate dead code introduced by earlier project‑scaffolding experiments.

After this change the supported project creation workflow remains:

```
wkb create-vault
```

No separate "project" abstraction remains in Workbench.

---

# Background

Earlier versions of Workbench supported project scaffolding via:

```
wkb create-project
wkb import-project
```

The current architecture treats a **vault as the project container**, making these commands redundant.

All project setup should now occur through:

```
create-vault
```

which installs:

- vault template
- `.obsidian` config
- `_common` symlink
- `_vault_registry`

---

# Removal Scope

The following modules should be removed **unless referenced elsewhere**.

## Primary CLI commands

Delete:

```
workbench/cli/create_project.py
workbench/cli/import_project.py
```

---

# CLI Registry Cleanup

Remove references from the command registry.

Check and update:

```
workbench/cli/__init__.py
workbench/cli/main.py
```

Delete any command registrations such as:

```python
register("create-project", ...)
register("import-project", ...)
```

Ensure the CLI help output no longer lists these commands.

---

# Dependency Sweep

Search for imports referencing the removed modules:

```
rg "create_project" workbench
rg "import_project" workbench
```

Remove any remaining imports or references.

If helper functions are shared with other commands, **move them to an appropriate utility module** instead of deleting them.

Examples to inspect:

```
_display_path
_parser
```

These were previously duplicated between `create_project` and `create_vault`.

Since `create-project` is deprecated, the canonical implementation should remain in:

```
workbench/cli/create_vault.py
```

---

# Asset and Template Review

Verify that no template or asset directories exist solely for the removed commands.

Search for references to:

```
assets/project-template
assets/project
```

If found and unused elsewhere, remove them.

Vault template assets must remain intact:

```
assets/vault-template
assets/obsidian-common
```

---

# Tests

Remove tests related only to the deprecated commands.

Search for:

```
test_create_project

test_import_project
```

Delete them if present.

Ensure remaining tests still pass, particularly:

- `test_create_vault`
- `test_vault_template_apply`

---

# Documentation Cleanup

Update documentation to remove references to the deprecated commands.

Check:

```
README.md
/docs
/dev
```

Replace any project scaffolding instructions with the current workflow:

```
wkb create-vault <path>
```

---

# Acceptance Criteria

The work order is complete when:

1. `create-project` command is removed.
2. `import-project` command is removed.
3. No CLI registry entries reference them.
4. No modules import their code.
5. All tests pass.
6. CLI help output reflects the updated command set.

---

# Suggested Commit

```
REWRITE remove deprecated create-project and import-project commands
```

---

# Expected Result

The Workbench CLI surface becomes:

```
wkb create-vault
wkb scan-sentinel
wkb stream
```

This aligns with the simplified architecture where:

```
vault = project container
```

and Workbench focuses on **vault tooling rather than project scaffolding**.

