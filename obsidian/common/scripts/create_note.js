module.exports = async function createNote(params = {}) {
  const app = resolveApp(params.app);
  const qa = params.quickAddApi || params.quickAdd || null;

  if (!app || !app.vault || !app.workspace) {
    return notice("Obsidian context not available.");
  }

  const templates = app.vault
    .getMarkdownFiles()
    .filter((file) => String(file.path || "").startsWith("_common/templates/"))
    .filter((file) => !String(file.basename || "").startsWith("_"));

  if (templates.length === 0) {
    return notice("No templates found in _common/templates.");
  }

  const menu = templates.map((file) => {
    const cache = app.metadataCache.getFileCache(file);
    const cls = cache?.frontmatter?.class;
    const className = typeof cls === "string" && cls.trim() ? cls.trim() : "template";
    return {
      file,
      label: `[${className}] ${file.basename}`,
    };
  });

  const selected = await pickTemplate(menu, qa);
  if (!selected) {
    return notice("Create note cancelled");
  }

  const rawTitle = await promptTitle(qa);
  const title = normalizeTitle(rawTitle);
  if (!title) {
    return notice("Title is required.");
  }

  const notePath = `${title}.md`;
  if (await app.vault.adapter.exists(notePath)) {
    return notice(`File already exists: ${notePath}`);
  }

  try {
    const templateContent = await app.vault.cachedRead(selected.file);
    const file = await app.vault.create(notePath, templateContent);
    const leaf = app.workspace.getLeaf?.(true);
    if (leaf && typeof leaf.openFile === "function") {
      await leaf.openFile(file);
    }
    return notice(`Created note: ${notePath}`);
  } catch (error) {
    const reason = error && error.message ? error.message : String(error);
    return notice(`Failed to create note: ${reason}`);
  }
};

async function pickTemplate(menu, qa) {
  if (qa && typeof qa.suggester === "function") {
    const labels = menu.map((item) => item.label);
    return qa.suggester(labels, menu, "Pick template");
  }

  if (menu.length === 1) {
    return menu[0];
  }

  return null;
}

async function promptTitle(qa) {
  if (qa && typeof qa.inputPrompt === "function") {
    return qa.inputPrompt("Note name");
  }

  if (typeof window !== "undefined" && typeof window.prompt === "function") {
    return window.prompt("Note name", "");
  }

  return "";
}

function normalizeTitle(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  return text.replace(/\.md$/i, "").replace(/[\\/]/g, "-").trim();
}

function resolveApp(candidateApp) {
  if (candidateApp && candidateApp.vault && candidateApp.workspace) {
    return candidateApp;
  }

  const globalApp = typeof window !== "undefined" ? window.app : null;
  if (globalApp && globalApp.vault && globalApp.workspace) {
    return globalApp;
  }

  return candidateApp;
}

function notice(message, timeout = 8000) {
  if (typeof Notice === "function") {
    new Notice(message, timeout);
  }
  console.log(message);
}
