// DO NOT USE — LEGACY MUTATION MODEL (PRE-NDJSON PIPELINE)

function notice(message, timeout = 8000) {
  if (typeof Notice === "function") new Notice(message, timeout);
  console.log(message);
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

function resolveQuickAdd(params = {}) {
  return params.quickAddApi || params.quickAdd || null;
}

function makeFail(prefix) {
  const tag = String(prefix || "Script").trim() || "Script";
  return function fail(message) {
    const text = `${tag} failed: ${message}`;
    if (typeof Notice === "function") new Notice(text, 10000);
    console.error(text);
  };
}

function isDataviewQueryNote(text) {
  return /```(?:dataview|dataviewjs)\b/i.test(String(text || ""));
}

function getVaultBasePath(app) {
  const adapter = app?.vault?.adapter;
  const basePath =
    (adapter && typeof adapter.getBasePath === "function" && adapter.getBasePath()) ||
    (adapter && adapter.basePath) ||
    "";
  if (!basePath) throw new Error("vault base path is unavailable");
  return String(basePath);
}

function resolveFileAbsolutePath(app, activeFile) {
  const path = require("path");
  return path.join(getVaultBasePath(app), String(activeFile?.path || ""));
}

function normalizeTopic(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/\.md$/i, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/-{2,}/g, "-");
}

function buildIdentity() {
  const alphabet = "abcdefghijklmnopqrstuvwxyz";
  let out = "";
  for (let index = 0; index < 8; index += 1) {
    out += alphabet[Math.floor(Math.random() * alphabet.length)];
  }
  return out;
}

function readVaultRegistry(app) {
  const fs = require("fs");
  const path = require("path");
  const registryPath = path.join(getVaultBasePath(app), "_vault_registry.json");
  if (!fs.existsSync(registryPath)) {
    return {};
  }

  try {
    return JSON.parse(fs.readFileSync(registryPath, "utf-8"));
  } catch (error) {
    throw new Error(`could not parse _vault_registry.json: ${error.message}`);
  }
}

function resolveVaultMnemonic(app) {
  try {
    const registry = readVaultRegistry(app);
    const raw = registry?.mnemonic || registry?.project_mnemonic || "";
    const mnemonic = normalizeTopic(raw);
    if (mnemonic) {
      return mnemonic;
    }
  } catch (error) {
    console.warn(error.message);
  }

  const path = require("path");
  return normalizeTopic(path.basename(getVaultBasePath(app))) || "vault";
}

function buildSlugForFile(app, file) {
  const domain = resolveVaultMnemonic(app);
  const topic = normalizeTopic(file?.basename || file?.name || "");
  if (!topic) {
    throw new Error(`could not derive slug topic from '${file?.path || "unknown file"}'`);
  }
  return `${domain}.${topic}.${buildIdentity()}`;
}

function buildSlugViaCli(app, activeFile) {
  return buildSlugForFile(app, activeFile);
}

function listTemplateMenu(app) {
  return app.vault
    .getMarkdownFiles()
    .filter((file) => String(file.path || "").startsWith("_common/templates/"))
    .filter((file) => !String(file.basename || "").startsWith("_"))
    .sort((left, right) => left.path.localeCompare(right.path))
    .map((file) => {
      const cache = app.metadataCache.getFileCache(file);
      const cls = cache?.frontmatter?.class;
      const className = typeof cls === "string" && cls.trim() ? cls.trim() : "template";
      return {
        file,
        label: `[${className}] ${file.basename}`,
      };
    });
}

async function pickTemplate(app, qa, placeholder = "Pick template") {
  const menu = listTemplateMenu(app);
  if (menu.length === 0) {
    throw new Error("no templates found in _common/templates");
  }

  if (qa && typeof qa.suggester === "function") {
    const labels = menu.map((item) => item.label);
    return qa.suggester(labels, menu, placeholder);
  }

  if (menu.length === 1) {
    return menu[0];
  }

  throw new Error("template picker requires QuickAdd suggester support");
}

async function confirmAction(qa, title, message) {
  if (qa && typeof qa.yesNoPrompt === "function") {
    try {
      return await qa.yesNoPrompt(title, message);
    } catch (_error) {
      return false;
    }
  }

  if (typeof window !== "undefined" && typeof window.confirm === "function") {
    return window.confirm(`${title}\n\n${message}`);
  }

  return false;
}

async function showSummary(qa, title, lines) {
  const rendered = Array.isArray(lines) ? lines : [String(lines || "")];
  if (qa && typeof qa.infoDialog === "function") {
    await qa.infoDialog(title, rendered);
    return;
  }

  notice([title, ...rendered].join("\n"), 12000);
}

function resolveCommandError(error) {
  const stderr = error?.stderr ? String(error.stderr).trim() : "";
  const stdout = error?.stdout ? String(error.stdout).trim() : "";
  return stderr || stdout || error?.message || String(error);
}

async function ensureSlug(app, file) {
  const cache = app.metadataCache.getFileCache(file);
  const current = cache?.frontmatter?.slug;
  if (isUsableSlug(current)) {
    return String(current).trim();
  }

  if (!app.fileManager || typeof app.fileManager.processFrontMatter !== "function") {
    throw new Error("Obsidian fileManager.processFrontMatter is unavailable");
  }

  const slug = buildSlugForFile(app, file);
  await app.fileManager.processFrontMatter(file, (frontmatter) => {
    if (!isUsableSlug(frontmatter.slug)) {
      frontmatter.slug = slug;
    }
  });
  return slug;
}

function isUsableSlug(value) {
  if (typeof value !== "string") {
    return false;
  }

  const normalized = value.trim().toLowerCase();
  return Boolean(
    normalized &&
      normalized !== "null" &&
      normalized !== "undefined" &&
      normalized !== "__slug__"
  );
}

async function applyTemplateToFiles(params = {}) {
  const app = resolveApp(params.app);
  if (!app || !app.vault || !app.workspace) {
    throw new Error("Obsidian app context not available");
  }

  const files = Array.isArray(params.files) ? params.files.filter(Boolean) : [];
  if (files.length === 0) {
    throw new Error("no markdown files were provided");
  }

  const template = params.template;
  if (!template || !template.file || !template.file.path) {
    throw new Error("template selection is required");
  }

  const summary = {
    template: template.file.path,
    processed: 0,
    updated: 0,
    failures: [],
  };

  const templateSpec = await loadTemplateSpec(app, template.file);

  for (const file of files) {
    try {
      const changed = await applyTemplateToFile(app, file, templateSpec);
      await ensureSlug(app, file);
      summary.processed += 1;
      if (changed) {
        summary.updated += 1;
      }
    } catch (error) {
      summary.failures.push({
        path: file.path,
        reason: resolveCommandError(error),
      });
    }
  }

  return summary;
}

async function loadTemplateSpec(app, templateFile) {
  const text = await readVaultFile(app, templateFile);
  const parsed = splitFrontmatter(text);
  if (!parsed.hasFrontmatter) {
    throw new Error(`template is missing frontmatter: ${templateFile.path}`);
  }

  const cache = app.metadataCache.getFileCache(templateFile);
  const frontmatter = sanitizeFrontmatter(cache?.frontmatter || {});

  return {
    file: templateFile,
    body: parsed.body,
    frontmatter,
    frontmatterBlock: parsed.frontmatterBlock,
  };
}

async function applyTemplateToFile(app, file, templateSpec) {
  const originalText = await readVaultFile(app, file);
  const parsedTarget = splitFrontmatter(originalText);

  if (!parsedTarget.hasFrontmatter) {
    const body = parsedTarget.body.trim() ? parsedTarget.body : templateSpec.body;
    const updated = composeFrontmatterDocument(templateSpec.frontmatterBlock, body);
    if (updated !== originalText) {
      await writeVaultFile(app, file, updated);
      return true;
    }
    return false;
  }

  if (!app.fileManager || typeof app.fileManager.processFrontMatter !== "function") {
    throw new Error("Obsidian fileManager.processFrontMatter is unavailable");
  }

  await app.fileManager.processFrontMatter(file, (frontmatter) => {
    mergeMissingFrontmatter(frontmatter, templateSpec.frontmatter);
  });

  let updatedText = await readVaultFile(app, file);
  let changed = updatedText !== originalText;

  const reparsed = splitFrontmatter(updatedText);
  if (reparsed.hasFrontmatter && !reparsed.body.trim() && templateSpec.body.trim()) {
    updatedText = composeFrontmatterDocument(reparsed.frontmatterBlock, templateSpec.body);
    await writeVaultFile(app, file, updatedText);
    changed = true;
  }

  return changed;
}

async function readVaultFile(app, file) {
  if (typeof app.vault.read === "function") {
    return app.vault.read(file);
  }
  return app.vault.cachedRead(file);
}

async function writeVaultFile(app, file, text) {
  return app.vault.modify(file, text);
}

function splitFrontmatter(text) {
  const normalized = String(text || "");
  if (!normalized.startsWith("---\n")) {
    return {
      hasFrontmatter: false,
      rawFrontmatter: "",
      frontmatterBlock: "",
      body: normalized,
    };
  }

  const endIndex = normalized.indexOf("\n---\n", 4);
  if (endIndex === -1) {
    return {
      hasFrontmatter: false,
      rawFrontmatter: "",
      frontmatterBlock: "",
      body: normalized,
    };
  }

  const rawFrontmatter = normalized.slice(4, endIndex);
  const frontmatterBlock = normalized.slice(0, endIndex + 5);
  const body = normalized.slice(endIndex + 5);
  return {
    hasFrontmatter: true,
    rawFrontmatter,
    frontmatterBlock,
    body,
  };
}

function composeFrontmatterDocument(frontmatterBlock, body) {
  const normalizedBody = String(body || "");
  const separator = normalizedBody.startsWith("\n") ? "" : "\n";
  return `${frontmatterBlock}${separator}${normalizedBody}`;
}

function sanitizeFrontmatter(frontmatter) {
  const cloned = cloneJsonLike(frontmatter || {});
  delete cloned.position;
  return cloned;
}

function mergeMissingFrontmatter(target, template) {
  for (const [key, value] of Object.entries(template || {})) {
    if (!(key in target)) {
      target[key] = cloneJsonLike(value);
      continue;
    }

    if (isPlainObject(target[key]) && isPlainObject(value)) {
      mergeMissingFrontmatter(target[key], value);
    }
  }
}

function cloneJsonLike(value) {
  if (typeof structuredClone === "function") {
    return structuredClone(value);
  }
  return JSON.parse(JSON.stringify(value));
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function markdownFilesFromPaths(app, paths) {
  const seen = new Set();
  const files = [];

  for (const rawPath of paths || []) {
    const path = String(rawPath || "").trim();
    if (!path || seen.has(path)) {
      continue;
    }
    seen.add(path);

    const file = app.vault.getAbstractFileByPath(path);
    if (!file || file.extension !== "md") {
      continue;
    }
    files.push(file);
  }

  return files;
}

function getActiveMarkdownFile(app) {
  const file = app.workspace.getActiveFile?.();
  if (file && file.extension === "md") {
    return file;
  }
  return null;
}

function getSelectedMarkdownFiles(app) {
  const leaves = app.workspace.getLeavesOfType?.("file-explorer") || [];
  const paths = new Set();

  for (const leaf of leaves) {
    const view = leaf?.view;
    const selection = view?.tree?.selectedDoms;
    if (selection && typeof selection.forEach === "function") {
      selection.forEach((item) => {
        const file = resolveSelectedExplorerFile(app, view, item);
        if (file?.extension === "md" && file.path) {
          paths.add(file.path);
        }
      });
    }

    if (paths.size === 0) {
      const container = view?.containerEl;
      if (!container || typeof container.querySelectorAll !== "function") {
        continue;
      }

      const nodes = Array.from(container.querySelectorAll(".tree-item-self.is-selected"));
      for (const node of nodes) {
        const file = resolveSelectedExplorerFile(app, view, {
          selfEl: node,
          el: node.parentElement || null,
        });
        if (file?.extension === "md" && file.path) {
          paths.add(file.path);
        }
      }
    }
  }

  return markdownFilesFromPaths(app, Array.from(paths));
}

function resolveSelectedExplorerFile(app, view, item) {
  if (!item) {
    return null;
  }

  if (item.file && item.file.extension) {
    return item.file;
  }

  if (typeof item.path === "string") {
    const byPath = app.vault.getAbstractFileByPath(item.path);
    if (byPath) {
      return byPath;
    }
  }

  const filesMap = view?.files;
  if (filesMap && typeof filesMap.get === "function") {
    const candidates = [item.el, item.selfEl?.parentElement, item.selfEl];
    for (const candidate of candidates) {
      if (!candidate) {
        continue;
      }
      const file = filesMap.get(candidate);
      if (file) {
        return file;
      }
    }
  }

  return null;
}

function getIngestMarkdownFiles(app) {
  return app.vault
    .getMarkdownFiles()
    .filter((file) => String(file.path || "").startsWith("_ingest/"))
    .sort((left, right) => left.path.localeCompare(right.path));
}

module.exports = {
  applyTemplateToFiles,
  buildSlugForFile,
  buildSlugViaCli,
  confirmAction,
  ensureSlug,
  getActiveMarkdownFile,
  getIngestMarkdownFiles,
  getSelectedMarkdownFiles,
  getVaultBasePath,
  isDataviewQueryNote,
  listTemplateMenu,
  makeFail,
  markdownFilesFromPaths,
  normalizeTopic,
  notice,
  pickTemplate,
  readVaultRegistry,
  resolveApp,
  resolveFileAbsolutePath,
  resolveQuickAdd,
  showSummary,
  splitFrontmatter,
};
