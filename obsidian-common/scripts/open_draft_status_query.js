// Obsidian macro: open the shared Draft Status query note.
// Designed for QuickAdd macro use.

module.exports = async function openDraftStatusQuery(params = {}) {
  const app = params.app || globalThis.app;
  if (!app || !app.vault || !app.workspace) {
    fail("Obsidian app context not available.");
    return;
  }

  const notify = (message, timeout = 8000) => {
    if (typeof Notice === "function") new Notice(message, timeout);
    console.log(message);
  };

  const candidatePaths = [
    "_common/queries/Draft Status.md",
    "_system/queries/Draft Status.md",
    "queries/Draft Status.md",
  ];

  let targetFile = null;
  for (const path of candidatePaths) {
    const file = app.vault.getAbstractFileByPath(path);
    if (file && file.extension === "md" && typeof file.path === "string") {
      targetFile = file;
      break;
    }
  }

  if (!targetFile) {
    fail("Could not locate Draft Status query note.");
    return;
  }

  const leaf = app.workspace.getLeaf?.(true) || app.workspace.activeLeaf;
  if (!leaf || typeof leaf.openFile !== "function") {
    fail("No workspace leaf available to open Draft Status.");
    return;
  }

  await leaf.openFile(targetFile);
  notify(`Opened: ${targetFile.path}`, 4000);
};

function fail(message) {
  const text = `Open Draft Status failed: ${message}`;
  if (typeof Notice === "function") new Notice(text, 10000);
  console.error(text);
}
