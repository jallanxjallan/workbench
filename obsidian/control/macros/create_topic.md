# Create Topic

Purpose: create a new topic note from `_control/templates/topic_template.md`.

## Expected Behavior

1. Prompt for note title.
2. Create a markdown note in the target vault.
3. Generate a slug in the canonical `<domain>.<topic>.<identity>` format.
4. Seed frontmatter and body from the topic template without mutating any existing note.

## Notes

- Canonical creation logic lives in `_control/macros/create_note.js`.
