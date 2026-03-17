const { spawnSync } = require("child_process");

module.exports = {
  runBatchMacro,
};

async function runBatchMacro(params = {}, verb = "compile") {
  const app = resolveApp(params.app);
  const tag = capitalize(verb);

  if (!app || !app.vault || !app.workspace) {
    throw new Error("Obsidian app context not available.");
  }

  const files = resolveExplicitSelections(app, params);
  if (files.length === 0) {
    throw new Error("No files selected for batch operation.");
  }

  const slugs = [];
  for (const file of files) {
    const slug = await extractSlug(app, file);
    if (!slug) {
      throw new Error(`File missing slug: ${file.name || file.basename || file.path}`);
    }
    slugs.push(slug);
  }

  if (slugs.length !== files.length) {
    throw new Error("Order serialization mismatch: selected file count does not match slug count.");
  }

  const batchId = buildBatchId(new Date());
  const message = buildCommitMessage(verb, batchId, slugs);
  runGitCommit(app, message);

  notice(`${tag} commit created: ${batchId}`, 10000);
  return {
    verb,
    batchId,
    message,
    files: files.map((file) => file.path),
    slugs,
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

function buildBatchId(date) {
  const yyyy = String(date.getFullYear());
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  const hh = String(date.getHours()).padStart(2, "0");
  const min = String(date.getMinutes()).padStart(2, "0");
  return `${yyyy}${mm}${dd}-${hh}${min}`;
}

function buildCommitMessage(verb, batchId, slugs) {
  const orderLines = slugs.map((slug, index) => `${index + 1} ${slug}`);
  return [
    `${verb}: ${batchId}`,
    "",
    `files: ${slugs.length}`,
    "",
    "order:",
    ...orderLines,
  ].join("\n");
}

function runGitCommit(app, message) {
  const cwd = getVaultBasePath(app);

  const result = spawnSync("git", ["-C", cwd, "commit", "--allow-empty", "-m", message], {
    cwd,
    stdio: "pipe",
    encoding: "utf8",
  });

  if (result.status === 0) {
    return;
  }

  const detail =
    String(result.stderr || "").trim() ||
    String(result.stdout || "").trim() ||
    result.error?.message ||
    "unknown git commit failure";
  throw new Error(`git commit failed: ${detail}`);
}

async function readVaultFile(app, file) {
  if (typeof app.vault.read === "function") return app.vault.read(file);
  return app.vault.cachedRead(file);
}

function getVaultBasePath(app) {
  const adapter = app?.vault?.adapter;
  const basePath =
    (adapter && typeof adapter.getBasePath === "function" && adapter.getBasePath()) ||
    adapter?.basePath ||
    "";

  if (!basePath) {
    throw new Error("vault base path is unavailable");
  }

  return String(basePath);
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

function capitalize(value) {
  const text = String(value || "").trim();
  return text ? `${text[0].toUpperCase()}${text.slice(1)}` : "Macro";
}
