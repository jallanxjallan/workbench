# Create Topic

Purpose: create a new topic note from `_control/templates/topic.md`.

## Expected Behavior

1. Prompt for note title.
2. Create a markdown note in the target vault.
3. Finalize the slug as `<prefix>.<project>.<hint>.<identity>` inside Obsidian JS.
4. Seed frontmatter and body from the topic template without mutating any existing note.

## Notes

- The template provides only the slug prefix.
- The project mnemonic comes from the vault-local `_vault_registry.json`.
- Canonical creation logic lives in `_control/macros/create_note.js`.
