const path = require("path");

module.exports = async function createNote(params = {}) {
  const app = resolveApp(params.app);
  const qa = params.quickAddApi || params.quickAdd || null;

  if (!app || !app.vault || !app.workspace) {
    throw new Error("Obsidian context not available.");
  }

  const slugHelper = loadSlugHelper(app);
  const template = await pickTemplate(app, qa, params);
  const rawTitle = await promptTitle(qa, params);
  const title = normalizeTitle(rawTitle);
  if (!title) {
    throw new Error("Title is required.");
  }

  const folder = normalizeFolder(params.folder || params.targetFolder || "");
  const notePath = folder ? `${folder}/${title}.md` : `${title}.md`;
  if (await app.vault.adapter.exists(notePath)) {
    throw new Error(`File already exists: ${notePath}`);
  }

  const templateText = await app.vault.cachedRead(template.file);
  const file = await app.vault.create(notePath, templateText);
  const slug = await slugHelper.finalize_file_slug({ app, file, sourceText: templateText });

  const leaf = app.workspace.getLeaf?.(true) || app.workspace.activeLeaf;
  if (leaf && typeof leaf.openFile === "function") {
    await leaf.openFile(file);
  }

  notice(`Created note: ${notePath}`, 8000);
  return {
    path: file.path,
    slug,
    template: template.file.path,
  };
};

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

function getVaultBasePath(app) {
  const adapter = app?.vault?.adapter;
  const basePath =
    (adapter && typeof adapter.getBasePath === "function" && adapter.getBasePath()) ||
    adapter?.basePath ||
    "";

  if (!basePath) {
    throw new Error("Vault base path is unavailable.");
  }

  return String(basePath);
}

function loadSlugHelper(app) {
  return require(path.join(getVaultBasePath(app), "_control", "scripts", "slug.js"));
}

function notice(message, timeout = 8000) {
  if (typeof Notice === "function") new Notice(message, timeout);
  console.log(message);
}

async function pickTemplate(app, qa, params = {}) {
  const requested = String(params.template || "").trim();
  if (requested) {
    const direct = app.vault.getAbstractFileByPath(requested);
    if (direct && direct.extension === "md") {
      return { file: direct, label: direct.basename };
    }

    const directControl = app.vault.getAbstractFileByPath(`_control/templates/${requested}`);
    if (directControl && directControl.extension === "md") {
      return { file: directControl, label: directControl.basename };
    }

    if (!requested.endsWith(".md")) {
      const withSuffix = app.vault.getAbstractFileByPath(`_control/templates/${requested}.md`);
      if (withSuffix && withSuffix.extension === "md") {
        return { file: withSuffix, label: withSuffix.basename };
      }
    }

    throw new Error(`Template not found: ${requested}`);
  }

  const templates = app.vault
    .getMarkdownFiles()
    .filter((file) => String(file.path || "").startsWith("_control/templates/"))
    .filter((file) => !String(file.basename || "").startsWith("_"))
    .sort((left, right) => left.path.localeCompare(right.path))
    .map((file) => {
      const cache = app.metadataCache.getFileCache(file);
      const cls = normalizeString(cache?.frontmatter?.class);
      return {
        file,
        label: cls ? `[${cls}] ${file.basename}` : file.basename,
      };
    });

  if (templates.length === 0) {
    throw new Error("No templates found in _control/templates.");
  }

  if (qa && typeof qa.suggester === "function") {
    return qa.suggester(
      templates.map((item) => item.label),
      templates,
      "Pick template",
    );
  }

  if (templates.length === 1) {
    return templates[0];
  }

  throw new Error("Template selection requires QuickAdd suggester support.");
}

async function promptTitle(qa, params = {}) {
  const preset = normalizeString(params.title);
  if (preset) return preset;

  if (qa && typeof qa.inputPrompt === "function") {
    return qa.inputPrompt("Note name");
  }

  if (typeof window !== "undefined" && typeof window.prompt === "function") {
    return window.prompt("Note name", "");
  }

  return "";
}

function normalizeTitle(value) {
  const text = normalizeString(value).replace(/\.md$/i, "");
  if (!text) return "";

  return text
    .replace(/[\\/]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .split(" ")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

function normalizeFolder(value) {
  return normalizeString(value).replace(/^\/+|\/+$/g, "");
}

function normalizeString(value) {
  return String(value || "").trim();
}
