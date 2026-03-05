// Obsidian macro: build and open an index note of all `_common/queries` notes.
// Intended for QuickAdd command execution.
const fail = makeFail("Open Common Query");

module.exports = async function openCommonQueryPicker(params = {}) {
  const app = params.app || globalThis.app;
  if (!app || !app.vault || !app.workspace) {
    return fail("Obsidian app context not available.");
  }

  try {
    const queryFiles = collectQueryFiles(app, "_common/queries");
    if (queryFiles.length === 0) {
      notice("No query notes found in _common/queries.", 9000);
      return;
    }

    const indexFile = await upsertQueryIndexNote(app, queryFiles);
    await openFileInNewLeaf(app, indexFile);
    notice(`Opened Common Query Index (${queryFiles.length}).`, 5000);
  } catch (error) {
    fail(error?.message || String(error));
  }
};

function collectQueryFiles(app, folderPrefix) {
  return app.vault
    .getMarkdownFiles()
    .filter((file) => file.path.startsWith(`${folderPrefix}/`))
    .sort((a, b) => a.path.localeCompare(b.path));
}

async function upsertQueryIndexNote(app, queryFiles) {
  const indexPath = "_common/queries/Common Query Index.md";
  const entries = queryFiles
    .filter((file) => file && file.path !== indexPath)
    .sort((a, b) => a.path.localeCompare(b.path));

  const bodyLines = entries.map((file) => {
    const target = String(file.path || "").replace(/\.md$/i, "");
    const label = file.basename || target;
    return `- [[${target}|${label}]]`;
  });

  const content = [
    "# Common Query Index",
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

function notice(message, timeout = 8000) {
  if (typeof Notice === "function") new Notice(message, timeout);
  console.log(message);
}

function makeFail(prefix) {
  const tag = String(prefix || "Script").trim() || "Script";
  return function fail(message) {
    const text = `${tag} failed: ${message}`;
    if (typeof Notice === "function") new Notice(text, 10000);
    console.error(text);
  };
}
