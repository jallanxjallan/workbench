module.exports = async (params = {}) => {
  const { app, quickAddApi } = params;
  const CLASS_OPTIONS = ["passage", "image", "caption", "scene", "note"];

  if (!app || !app.vault || !app.workspace || !quickAddApi) {
    return notice("Obsidian or QuickAdd context not available.");
  }

  const chosenClass = await quickAddApi.suggester(CLASS_OPTIONS, CLASS_OPTIONS);
  if (!chosenClass) {
    return notice("Template insertion cancelled");
  }

  const file = app.workspace.getActiveFile();
  if (!file) {
    return notice("No active file");
  }

  const content = await app.vault.read(file);
  const hasFrontmatter = content.startsWith("---");
  const templateRaw = await app.vault.adapter.read("_common/templates/content_item.md");
  const template = templateRaw.replace("__CLASS__", chosenClass);

  if (!hasFrontmatter) {
    await app.vault.modify(file, `${template}\n${content}`);
    return notice("Content template inserted");
  }

  await app.commands.executeCommandById("templater-obsidian:run-templater-merge-content");
};

function notice(message, timeout = 8000) {
  if (typeof Notice === "function") {
    new Notice(message, timeout);
  }
  console.log(message);
}
