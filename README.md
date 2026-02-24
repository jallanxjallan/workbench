# Workbench

Runtime toolchain repository for CLI stream adapters, shell integration, vault workflows, and backup orchestration.

## Pandoc Integration Policy

Workbench does **not** own Pandoc filters/templates internally.

- Pandoc assets and filter logic live in the standalone `pandoc-toolchain` repository.
- Workbench invokes Pandoc via CLI only.
- Workbench does not import Pandoc filter modules from its own Python package.

### Local Symlink For Editing

Workbench may expose a local convenience symlink:

```bash
cd ~/Workbench
ln -sfn "$HOME/.local/share/pandoc" pandoc-data
```

`pandoc-data` is local-only and ignored by git. It is not owned by Workbench.

### CLI Invocation Pattern

Use explicit data-dir wiring:

```bash
pandoc "$INPUT.md" \
  --data-dir "$PWD/pandoc-data" \
  --template default \
  --lua-filter "$PWD/pandoc-data/filters/lua/content-filtering/filter_components.lua" \
  -o "$OUTPUT.pdf"
```

Optional shell helper:

```bash
wb-pandoc() {
  pandoc --data-dir "$PWD/pandoc-data" "$@"
}
```

## Ownership Boundaries

- In scope: CLI orchestration, stream adapters, shell lifecycle, vault logic, backups.
- Out of scope: Pandoc filter/template/reference implementation.
