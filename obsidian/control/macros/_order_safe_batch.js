module.exports = {
  runBatchMacro,
};

async function runBatchMacro(params = {}, verb = "compile") {
  const app = resolveApp(params.app);
  const label = capitalize(verb);

  if (!app || !app.vault || !app.workspace) {
    throw new Error("Obsidian app context not available.");
  }

  const files = resolveExplicitSelections(app, params);
  if (files.length === 0) {
    throw new Error("No files selected for batch operation.");
  }

  const slugs = [];
  const missing = [];

  for (const file of files) {
    const slug = await extractSlug(app, file);
    slugs.push(slug);
    if (!slug) {
      missing.push(file.path);
    }
  }

  if (missing.length > 0) {
    warnOnly(
      `${label}: ${missing.length} selected file(s) have no slug yet. Pre-template state is valid.`,
      10000,
    );
  }

  notice(
    `${label} selection prepared: ${files.length} file(s). Workbench owns batch ids and execution.`,
    8000,
  );

  return {
    files: files.map((file) => file.path),
    slugs,
    ordered: true,
  };
}

function resolveExplicitSelections(app, params = {}) {
  const explicitFiles =
    coerceFiles(app, params.files) ||
    coerceFiles(app, params.selectedFiles) ||
    coerceFiles(app, params.paths) ||
    coerceFiles(app, params.selectedPaths);

  if (explicitFiles && explicitFiles.length > 0) {
    return explicitFiles;
  }

  return getExplorerSelectedMarkdownFiles(app);
}

function coerceFiles(app, source) {
  if (!Array.isArray(source) || source.length === 0) return null;

  const files = [];
  const seen = new Set();

  for (const item of source) {
    const file =
      item && typeof item === "object" && typeof item.path === "string"
        ? item
        : app.vault.getAbstractFileByPath(String(item || "").trim());

    if (!file || file.extension !== "md" || !file.path) {
      continue;
    }

    if (seen.has(file.path)) {
      throw new Error("Duplicate file selection detected");
    }

    seen.add(file.path);
    files.push(file);
  }

  return files;
}

function getExplorerSelectedMarkdownFiles(app) {
  const ordered = [];
  const seen = new Set();
  const leaves = app.workspace.getLeavesOfType?.("file-explorer") || [];

  for (const leaf of leaves) {
    const view = leaf?.view;
    const selection = view?.tree?.selectedDoms;

    if (selection && typeof selection.forEach === "function") {
      selection.forEach((item) => {
        pushFile(resolveSelectedExplorerFile(app, view, item));
      });
    }

    if (ordered.length > 0) continue;

    const container = view?.containerEl;
    if (!container || typeof container.querySelectorAll !== "function") {
      continue;
    }

    const nodes = Array.from(container.querySelectorAll(".tree-item-self.is-selected"));
    for (const node of nodes) {
      pushFile(
        resolveSelectedExplorerFile(app, view, {
          selfEl: node,
          el: node.parentElement || null,
        }),
      );
    }
  }

  return ordered;

  function pushFile(file) {
    if (!file || file.extension !== "md" || !file.path) return;
    if (seen.has(file.path)) {
      throw new Error("Duplicate file selection detected");
    }
    seen.add(file.path);
    ordered.push(file);
  }
}

function resolveSelectedExplorerFile(app, view, item) {
  if (!item) return null;
  if (item.file && item.file.extension) return item.file;

  if (typeof item.path === "string") {
    const direct = app.vault.getAbstractFileByPath(item.path);
    if (direct) return direct;
  }

  const filesMap = view?.files;
  if (filesMap && typeof filesMap.get === "function") {
    const candidates = [item.el, item.selfEl?.parentElement, item.selfEl];
    for (const candidate of candidates) {
      if (!candidate) continue;
      const file = filesMap.get(candidate);
      if (file) return file;
    }
  }

  return null;
}

async function extractSlug(app, file) {
  const cached = normalizeSlug(app.metadataCache.getFileCache(file)?.frontmatter?.slug);
  if (cached) return cached;

  const text = await readVaultFile(app, file);
  return normalizeSlug(extractFrontmatterSlug(text));
}

function extractFrontmatterSlug(text) {
  const normalized = String(text || "");
  if (!normalized.startsWith("---\n")) return "";

  const end = normalized.indexOf("\n---\n", 4);
  if (end === -1) return "";

  const block = normalized.slice(4, end);
  const match = block.match(/(?:^|\n)slug:\s*(.+?)\s*(?:\n|$)/);
  return match ? match[1] : "";
}

function normalizeSlug(value) {
  const slug = String(value || "").trim().replace(/^['"]|['"]$/g, "");
  if (!slug || slug === "null" || slug === "undefined") return "";
  return slug;
}

async function readVaultFile(app, file) {
  if (typeof app.vault.read === "function") return app.vault.read(file);
  return app.vault.cachedRead(file);
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
  if (typeof Notice === "function") new Notice(message, timeout);
  console.log(message);
}

function warnOnly(message, timeout = 10000) {
  if (typeof Notice === "function") new Notice(message, timeout);
  console.warn(message);
}

function capitalize(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  return text[0].toUpperCase() + text.slice(1);
}
