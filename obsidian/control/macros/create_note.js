const path = require("path");

module.exports = async function createNote(params = {}) {
  const app = resolveApp(params.app);
  const qa = params.quickAddApi || params.quickAdd || null;

  if (!app || !app.vault || !app.workspace) {
    throw new Error("Obsidian context not available.");
  }

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
  const slug = buildSlug(app, title);
  const rendered = injectSlug(templateText, slug);
  const file = await app.vault.create(notePath, rendered);

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
  return text.replace(/[\\/]/g, "-").trim();
}

function normalizeFolder(value) {
  return normalizeString(value).replace(/^\/+|\/+$/g, "");
}

function normalizeString(value) {
  return String(value || "").trim();
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

function readVaultRegistry(app) {
  const fs = require("fs");
  const registryPath = path.join(getVaultBasePath(app), "_vault_registry.json");
  if (!fs.existsSync(registryPath)) {
    throw new Error("Vault registry is missing: _vault_registry.json");
  }
  return JSON.parse(fs.readFileSync(registryPath, "utf8"));
}

function resolveVaultMnemonic(app) {
  const registry = readVaultRegistry(app);
  const mnemonic = normalizeString(registry?.mnemonic || registry?.project_mnemonic || "");
  if (!mnemonic) {
    throw new Error("Vault mnemonic is missing from _vault_registry.json");
  }
  return mnemonic.toLowerCase();
}

function normalizeTopic(value) {
  return normalizeString(value)
    .toLowerCase()
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

function buildSlug(app, title) {
  const domain = resolveVaultMnemonic(app);
  const topic = normalizeTopic(title);
  if (!topic) {
    throw new Error("Could not derive slug topic from note title.");
  }
  return `${domain}.${topic}.${buildIdentity()}`;
}

function injectSlug(sourceText, slug) {
  const normalized = String(sourceText || "");
  if (!normalized.startsWith("---\n")) {
    return `---\nslug: ${slug}\n---\n\n${normalized}`;
  }

  const end = normalized.indexOf("\n---\n", 4);
  if (end === -1) {
    return `---\nslug: ${slug}\n---\n\n${normalized}`;
  }

  const block = normalized.slice(4, end);
  const body = normalized.slice(end + 5);
  const lines = block.split("\n");
  let sawSlug = false;

  for (let index = 0; index < lines.length; index += 1) {
    if (!/^slug\s*:/.test(lines[index])) {
      continue;
    }

    const existing = normalizeString(lines[index].slice(lines[index].indexOf(":") + 1)).replace(
      /^['"]|['"]$/g,
      "",
    );
    if (existing) {
      throw new Error("Template already defines a concrete slug.");
    }
    lines[index] = `slug: ${slug}`;
    sawSlug = true;
    break;
  }

  if (!sawSlug) {
    lines.unshift(`slug: ${slug}`);
  }

  return `---\n${lines.join("\n")}\n---\n${body}`;
}
