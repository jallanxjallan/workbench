// Obsidian macro: list Dataview query notes in _common/queries as clickable refs.
// Intended for QuickAdd command execution.

module.exports = async function listCommonDataviewQueries(params = {}) {
  const app = params.app || globalThis.app;
  if (!app || !app.vault || !app.workspace) {
    fail("Obsidian app context not available.");
    return;
  }

  const notify = (message, timeout = 8000) => {
    if (typeof Notice === "function") new Notice(message, timeout);
    console.log(message);
  };

  try {
    const queryFiles = await collectDataviewQueryFiles(app, "_common/queries");
    if (queryFiles.length === 0) {
      notify("No Dataview queries found in _common/queries.", 9000);
      return;
    }

    const indexFile = await upsertQueryIndexNote(app, queryFiles);
    await openFileInNewLeaf(app, indexFile);
    notify(`Opened Dataview Query Index (${queryFiles.length}).`, 5000);
  } catch (error) {
    fail(error?.message || String(error));
  }
};

async function collectDataviewQueryFiles(app, folderPrefix) {
  const files = app.vault
    .getMarkdownFiles()
    .filter((file) => file.path.startsWith(`${folderPrefix}/`))
    .sort((a, b) => a.path.localeCompare(b.path));

  const out = [];
  for (const file of files) {
    const text = await app.vault.cachedRead(file);
    if (isDataviewQueryNote(text)) out.push(file);
  }
  return out;
}

function isDataviewQueryNote(text) {
  return /```(?:dataview|dataviewjs)\b/i.test(String(text || ""));
}

async function upsertQueryIndexNote(app, queryFiles) {
  const indexPath = "_common/queries/Dataview Query Index.md";
  const entries = queryFiles
    .filter((file) => file && file.path !== indexPath)
    .sort((a, b) => a.path.localeCompare(b.path));

  const bodyLines = entries.map((file) => {
    const target = String(file.path || "").replace(/\.md$/i, "");
    const label = file.basename || target;
    return `- [[${target}|${label}]]`;
  });

  const content = [
    "# Dataview Query Index",
    "",
    `Total: ${entries.length}`,
    "",
    ...bodyLines,
    "",
  ].join("\n");

  const existing = app.vault.getAbstractFileByPath(indexPath);
  if (!existing) {
    return app.vault.create(indexPath, content);
  }

  if (existing.extension !== "md") {
    throw new Error(`Index path exists but is not a markdown file: ${indexPath}`);
  }

  const current = await app.vault.cachedRead(existing);
  if (current !== content) {
    await app.vault.modify(existing, content);
  }

  return existing;
}

async function openFileInNewLeaf(app, file) {
  const leaf = app.workspace.getLeaf?.(true) || app.workspace.activeLeaf;
  if (!leaf || typeof leaf.openFile !== "function") {
    throw new Error("No workspace leaf available.");
  }
  await leaf.openFile(file);
}

function fail(message) {
  const text = `List Dataview Queries failed: ${message}`;
  if (typeof Notice === "function") new Notice(text, 10000);
  console.error(text);
}
