<%*
/*
Dynamic template picker

Creates a note from any template in _common/templates.
Templates remain pure Markdown.

Compatible with:
- Obsidian Templater
- wkb writenew
*/

const TEMPLATE_FOLDER = "_common/templates";

const templates = app.vault
  .getMarkdownFiles()
  .filter((file) => file.path.startsWith(`${TEMPLATE_FOLDER}/`))
  .filter((file) => !file.basename.startsWith("_"));

if (templates.length === 0) {
  new Notice("No templates found");
  return;
}

const labels = templates.map((templateFile) => {
  const cache = app.metadataCache.getFileCache(templateFile);
  const cls = cache?.frontmatter?.class;
  const tag = typeof cls === "string" && cls.trim() ? cls.trim() : "template";
  return `[${tag}] ${templateFile.basename}`;
});

const choice = await tp.system.suggester(labels, templates);
if (!choice) {
  return;
}

const title = await tp.system.prompt("Note name");
if (!title || !title.trim()) {
  return;
}

await tp.file.create_new(choice, title.trim(), false);
%>
