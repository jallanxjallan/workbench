const fs = require("fs");
const path = require("path");

const ALPHABET = "abcdefghijklmnopqrstuvwxyz";
const VAULT_REGISTRY_FILE = "_vault_registry.json";

function normalizeString(value) {
  return String(value || "").trim();
}

function stripQuotes(value) {
  return normalizeString(value).replace(/^['"]|['"]$/g, "");
}

function randomAlpha(length = 8) {
  let output = "";
  for (let index = 0; index < length; index += 1) {
    const offset = Math.floor(Math.random() * ALPHABET.length);
    output += ALPHABET[offset];
  }
  return output;
}

function getApp(candidate) {
  if (candidate?.vault?.adapter) {
    return candidate;
  }

  if (typeof window !== "undefined" && window?.app?.vault?.adapter) {
    return window.app;
  }

  return null;
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

function readVaultRegistry(app) {
  const registryPath = path.join(getVaultBasePath(app), VAULT_REGISTRY_FILE);
  if (!fs.existsSync(registryPath)) {
    throw new Error(`Vault registry is missing: ${VAULT_REGISTRY_FILE}`);
  }

  try {
    return JSON.parse(fs.readFileSync(registryPath, "utf8"));
  } catch (error) {
    const message = error && error.message ? error.message : String(error);
    throw new Error(`Could not parse ${VAULT_REGISTRY_FILE}: ${message}`);
  }
}

function resolveProjectMnemonic(app) {
  const registry = readVaultRegistry(app);
  const mnemonic = normalizeString(registry?.mnemonic || registry?.project_mnemonic || "")
    .toLowerCase()
    .replace(/[^a-z]+/g, "");

  if (!mnemonic) {
    throw new Error(
      `Vault mnemonic is missing from ${VAULT_REGISTRY_FILE} or does not normalize to lowercase letters.`,
    );
  }

  return mnemonic;
}

function normalizeContext(value) {
  const context = normalizeString(value)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/-{2,}/g, "-");

  if (!context) {
    throw new Error("Context normalized to an empty value.");
  }

  return context;
}

function resolveContext(app, fallback = "") {
  const registry = readVaultRegistry(app);
  const candidates = ["context", "default_context", "slug_context", "project_context"];

  for (const key of candidates) {
    const value = registry?.[key];
    if (typeof value !== "string" || !value.trim()) {
      continue;
    }
    return normalizeContext(value);
  }

  if (normalizeString(fallback)) {
    return normalizeContext(fallback);
  }

  return "";
}

function normalizeHint(value) {
  const hint = normalizeString(value)
    .replace(/\.md$/i, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/-{2,}/g, "-");

  if (!hint) {
    throw new Error("Could not derive slug hint from filename.");
  }

  return hint;
}

function locateFrontmatter(sourceText) {
  const normalized = String(sourceText || "");
  if (!normalized.startsWith("---\n")) {
    return null;
  }

  const end = normalized.indexOf("\n---\n", 4);
  if (end === -1) {
    return null;
  }

  return {
    block: normalized.slice(4, end),
    body: normalized.slice(end + 5),
  };
}

function escapePattern(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function readFrontmatterValue(sourceText, field) {
  const frontmatter = locateFrontmatter(sourceText);
  if (!frontmatter) {
    return "";
  }

  const matcher = new RegExp(`^${escapePattern(field)}\\s*:(.*)$`);
  const lines = frontmatter.block.split("\n");
  for (const line of lines) {
    const match = line.match(matcher);
    if (match) {
      return stripQuotes(match[1]);
    }
  }

  return "";
}

function readSlugPrefix(sourceText) {
  const raw = readFrontmatterValue(sourceText, "slug");
  if (!raw) {
    return null;
  }

  const prefix = raw.toLowerCase().replace(/[^a-z]+/g, "");
  if (!prefix) {
    throw new Error("Template slug prefix must contain lowercase letters.");
  }

  return prefix;
}

function replaceFrontmatterField(sourceText, field, value) {
  const frontmatter = locateFrontmatter(sourceText);
  if (!frontmatter) {
    throw new Error("Template frontmatter is required.");
  }

  const matcher = new RegExp(`^${escapePattern(field)}\\s*:`);
  const lines = frontmatter.block.split("\n");
  let updated = false;

  for (let index = 0; index < lines.length; index += 1) {
    if (!matcher.test(lines[index])) {
      continue;
    }

    lines[index] = `${field}: ${value}`;
    updated = true;
    break;
  }

  if (!updated) {
    throw new Error(`Template must declare a ${field} field.`);
  }

  return `---\n${lines.join("\n")}\n---\n${frontmatter.body}`;
}

async function listExistingSlugs(app, excludePath = "") {
  const existing = new Set();
  const files = app?.vault?.getMarkdownFiles ? app.vault.getMarkdownFiles() : [];

  for (const file of files) {
    if (excludePath && file.path === excludePath) {
      continue;
    }

    let slug = stripQuotes(app?.metadataCache?.getFileCache(file)?.frontmatter?.slug);
    if (!slug) {
      try {
        slug = readFrontmatterValue(await app.vault.cachedRead(file), "slug");
      } catch (_error) {
        slug = "";
      }
    }

    if (slug) {
      existing.add(slug);
    }
  }

  return existing;
}

async function buildUniqueSlug({ app, sourceText, filePath, excludePath = "" }) {
  const prefix = readSlugPrefix(sourceText);
  if (!prefix) {
    return null;
  }

  const context = resolveProjectMnemonic(app);
  const hint = normalizeHint(path.basename(String(filePath || ""), path.extname(String(filePath || ""))));
  const existing = await listExistingSlugs(app, excludePath);

  for (let attempt = 0; attempt < 40; attempt += 1) {
    const slug = `${prefix}.${context}.${hint}.${randomAlpha(8)}`;
    if (!existing.has(slug)) {
      return slug;
    }
  }

  throw new Error("Could not generate a unique slug after 40 attempts.");
}

async function finalizeFileSlug({ app: candidateApp, file, sourceText } = {}) {
  const app = getApp(candidateApp);
  if (!app || !file) {
    throw new Error("Obsidian app context and file are required for slug finalization.");
  }

  const text = sourceText || (await app.vault.cachedRead(file));
  const prefix = readSlugPrefix(text);
  if (!prefix) {
    return null;
  }

  const slug = await buildUniqueSlug({
    app,
    sourceText: text,
    filePath: file.path,
    excludePath: file.path,
  });
  const updated = replaceFrontmatterField(text, "slug", slug);
  if (updated !== text) {
    await app.vault.modify(file, updated);
  }
  return slug;
}

async function generateSlug(appOrOptions, maybeOptions = {}) {
  let app = getApp(appOrOptions);
  let options = maybeOptions;

  if (!app) {
    options = appOrOptions || {};
    app = getApp(options.app);
  }

  if (!app) {
    throw new Error("Obsidian app context is required for slug generation.");
  }

  const prefixSource = options.sourceText || (options.prefix ? `---\nslug: ${options.prefix}\n---\n` : "");
  return buildUniqueSlug({
    app,
    sourceText: prefixSource,
    filePath: options.filePath || options.file?.path || options.title || "untitled.md",
    excludePath: options.excludePath || options.file?.path || "",
  });
}

module.exports = {
  finalize_file_slug: finalizeFileSlug,
  generate_slug: generateSlug,
  normalize_hint: normalizeHint,
  read_slug_prefix: readSlugPrefix,
  replace_frontmatter_field: replaceFrontmatterField,
  resolve_context: resolveContext,
  resolve_project_mnemonic: resolveProjectMnemonic,
};
