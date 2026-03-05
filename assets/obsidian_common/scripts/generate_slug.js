// QuickAdd dispatcher macro:
// - Accept selected filepaths from DataviewJS/QuickAdd variables.
// - Derive namespace behavior from file frontmatter (with vault fallback).
// - Delegate slug mutation/validation to `wkb slug ensure`.
function notice(message, timeout = 8000) {
  if (typeof Notice === "function") new Notice(message, timeout);
  console.log(message);
}

function fail(message) {
  const text = `generate_slug failed: ${message}`;
  if (typeof Notice === "function") new Notice(text, 10000);
  console.error(text);
}

module.exports = async function generateSlug(params = {}) {
  const app = params.app || globalThis.app;
  if (!app || !app.vault || !app.metadataCache) {
    return fail("Obsidian app context not available.");
  }

  const filepaths = collectFilepaths(params, app);
  if (filepaths.length === 0) {
    return fail("No filepaths were provided.");
  }

  const vaultNamespace = resolveVaultNamespace(app);
  let created = 0;
  let validated = 0;
  let failed = 0;

  for (const absolutePath of filepaths) {
    try {
      await prepareFileForEnsure(app, absolutePath);
      const derived = deriveSlugArgs(app, absolutePath, vaultNamespace);
      const output = ensureSlugViaCli(absolutePath, derived.namespace);
      const counters = parseEnsureCounters(output);
      created += counters.created;
      validated += counters.validated;
      failed += counters.failed;
    } catch (error) {
      failed += 1;
      console.error(error);
    }
  }

  notice(
    `generate_slug complete. Created: ${created}. Validated: ${validated}. Failed: ${failed}.`,
    10000,
  );
};

function collectFilepaths(params, app) {
  const vars = params.variables || {};
  const candidates = [
    params.filepaths,
    params.files,
    params.selectedFiles,
    vars.filepaths,
    vars.files,
    vars.selectedFiles,
    globalThis.__wkbSlugFilepaths,
  ];

  const values = [];
  for (const candidate of candidates) flattenCandidate(candidate, values);

  const out = [];
  const seen = new Set();
  for (const value of values) {
    const abs = toAbsolutePath(app, value);
    if (!abs || seen.has(abs)) continue;
    seen.add(abs);
    out.push(abs);
  }
  return out;
}

function flattenCandidate(candidate, out) {
  if (candidate == null) return;

  if (Array.isArray(candidate)) {
    for (const item of candidate) flattenCandidate(item, out);
    return;
  }

  if (typeof candidate === "object") {
    if (typeof candidate.path === "string") out.push(candidate.path);
    if (candidate.file && typeof candidate.file.path === "string") {
      out.push(candidate.file.path);
    }
    return;
  }

  const text = String(candidate).trim();
  if (!text) return;

  if (text.startsWith("[") || text.startsWith("{")) {
    try {
      const parsed = JSON.parse(text);
      flattenCandidate(parsed, out);
      return;
    } catch (_) {
      // fall through to line splitting
    }
  }

  const parts = text
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
  for (const part of parts) out.push(part);
}

function toAbsolutePath(app, rawPath) {
  const value = String(rawPath || "").trim();
  if (!value) return "";

  const path = require("path");
  if (path.isAbsolute(value)) return path.normalize(value);

  const adapter = app.vault && app.vault.adapter;
  const basePath =
    (adapter &&
      typeof adapter.getBasePath === "function" &&
      adapter.getBasePath()) ||
    (adapter && adapter.basePath) ||
    "";
  if (!basePath) return "";
  return path.resolve(basePath, value);
}

function toVaultRelativePath(app, absolutePath) {
  const path = require("path");
  const adapter = app.vault && app.vault.adapter;
  const basePath =
    (adapter &&
      typeof adapter.getBasePath === "function" &&
      adapter.getBasePath()) ||
    (adapter && adapter.basePath) ||
    "";
  if (!basePath) return "";

  const relative = path.relative(basePath, absolutePath);
  if (!relative || relative.startsWith("..")) return "";
  return relative.split(path.sep).join("/");
}

async function prepareFileForEnsure(app, absolutePath) {
  const rel = toVaultRelativePath(app, absolutePath);
  if (!rel) return;

  const file = app.vault.getAbstractFileByPath(rel);
  if (!file || file.extension !== "md") return;

  const original = await app.vault.read(file);
  const updated = stripPlaceholderSlugLine(original);
  if (updated !== original) {
    await app.vault.modify(file, updated);
  }
}

function resolveVaultNamespace(app) {
  const path = require("path");
  const fs = require("fs");
  const adapter = app.vault && app.vault.adapter;
  const basePath =
    (adapter &&
      typeof adapter.getBasePath === "function" &&
      adapter.getBasePath()) ||
    (adapter && adapter.basePath) ||
    "";
  if (!basePath) return "";

  const registryPath = path.join(basePath, "_vault_registry.json");
  if (!fs.existsSync(registryPath)) return "";

  try {
    const parsed = JSON.parse(fs.readFileSync(registryPath, "utf-8"));
    return normalizeValue(parsed && parsed.mnemonic);
  } catch (_) {
    return "";
  }
}

function deriveSlugArgs(app, absolutePath, vaultNamespace) {
  const rel = toVaultRelativePath(app, absolutePath);
  const file = rel ? app.vault.getAbstractFileByPath(rel) : null;
  const frontmatter = file
    ? app.metadataCache.getFileCache(file)?.frontmatter || {}
    : {};

  const className = normalizeValue(frontmatter.class);
  const isInstruction = className === "instruction";
  const scope = normalizeValue(frontmatter.scope);

  let namespace = firstNonEmpty(
    frontmatter.namespace,
    frontmatter.ns,
    frontmatter.slug_namespace,
    frontmatter.mnemonic,
  );
  namespace = normalizeValue(namespace);

  if (!namespace) {
    if (!isInstruction) namespace = vaultNamespace;
    else if (scope !== "global") namespace = vaultNamespace;
  }

  return { namespace };
}

function ensureSlugViaCli(absolutePath, namespace) {
  const { execFileSync } = require("child_process");
  const args = ["slug", "ensure", absolutePath];
  if (namespace) args.push("--namespace", namespace);

  const wkbCandidates = resolveWkbCandidates();
  let lastError = null;

  for (const wkbBin of wkbCandidates) {
    try {
      return String(
        execFileSync(wkbBin, args, {
          encoding: "utf-8",
          stdio: ["ignore", "pipe", "pipe"],
        }) || "",
      ).trim();
    } catch (error) {
      const detail = error && error.message ? String(error.message) : "";
      if (/ENOENT/i.test(detail)) {
        lastError = error;
        continue;
      }

      const stderr = error && error.stderr ? String(error.stderr).trim() : "";
      const reason = stderr || detail || "unknown error";
      throw new Error(`Slug ensure failed via '${wkbBin}': ${reason}`);
    }
  }

  const msg =
    (lastError && lastError.message ? String(lastError.message) : "") ||
    "wkb binary not found";
  throw new Error(
    `Slug ensure failed: unable to locate 'wkb'. Set WKB_BIN env or install wkb on PATH. (${msg})`,
  );
}

function resolveWkbCandidates() {
  const os = require("os");
  const path = require("path");
  const candidates = [];
  const envBin = String(process.env.WKB_BIN || "").trim();
  if (envBin) candidates.push(envBin);

  candidates.push(path.join(os.homedir(), "Python3.13Env", "bin", "wkb"));
  candidates.push("wkb");
  return uniqueStrings(candidates);
}

function parseEnsureCounters(output) {
  let created = 0;
  let validated = 0;
  let failed = 0;

  for (const line of String(output || "").split(/\r?\n/)) {
    const text = line.trim().toLowerCase();
    if (text.startsWith("created:")) {
      created += parseCountValue(text.slice("created:".length));
    } else if (text.startsWith("validated:")) {
      validated += parseCountValue(text.slice("validated:".length));
    } else if (text.startsWith("failed:")) {
      failed += parseCountValue(text.slice("failed:".length));
    }
  }

  return { created, validated, failed };
}

function parseCountValue(value) {
  const n = Number.parseInt(String(value || "").trim(), 10);
  return Number.isFinite(n) ? n : 0;
}

function normalizeValue(value) {
  return String(value == null ? "" : value).trim().toLowerCase();
}

function firstNonEmpty(...values) {
  for (const value of values) {
    const text = String(value == null ? "" : value).trim();
    if (text) return text;
  }
  return "";
}

function uniqueStrings(values) {
  const out = [];
  const seen = new Set();
  for (const value of values) {
    const text = String(value || "").trim();
    if (!text || seen.has(text)) continue;
    seen.add(text);
    out.push(text);
  }
  return out;
}

function stripPlaceholderSlugLine(text) {
  const source = String(text || "");
  const match = source.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!match) return source;

  const newline = source.includes("\r\n") ? "\r\n" : "\n";
  const yaml = String(match[1] || "");
  const cleaned = yaml
    .split(/\r?\n/)
    .filter(
      (line) =>
        !/^\s*slug\s*:\s*(?:['"]?__slug__['"]?|null|~)?\s*$/i.test(line),
    )
    .join(newline);

  if (cleaned === yaml) return source;
  const replacement = `---${newline}${cleaned}${newline}---`;
  return source.replace(/^---\r?\n[\s\S]*?\r?\n---/, replacement);
}
