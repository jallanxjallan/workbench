# Core

`core/` is the copyable vault skeleton for Obsidian.

It contains the files Workbench installs directly into each vault, including:

- `.obsidian/`
- plugin manifests and plugin data defaults
- shared hotkeys and other vault runtime settings

`control/` is separate on purpose.

- `core/` gets copied into a vault
- `control/` is mounted into a vault as the `_control` symlink target
