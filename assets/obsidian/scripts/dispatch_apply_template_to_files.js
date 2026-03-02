// QuickAdd dispatcher macro:
// - Accept filepaths from DataviewJS/QuickAdd variables.
// - Prompt for a template.
// - Delegate all file mutation to `wkb vault template apply`.
const { notice, makeFail } = require("./_shared");

const fail = makeFail("Dispatch Apply Template");

module.exports = async function dispatchApplyTemplateToFiles(params = {}) {
  const app = params.app || globalThis.app;
  const qa =
    params.quickAddApi ||
    params.quickAdd ||
    app?.plugins?.plugins?.quickadd?.api;

  if (!app || !app.vault || !app.metadataCache) {
    return fail("Obsidian app context not available.");
  }
  if (!qa || typeof qa.suggester !== "function") {
    return fail("QuickAdd API not available.");
  }

  const filepaths = collectFilepaths(params, app);
  if (filepaths.length === 0) {
    return fail("No filepaths were provided to the dispatcher.");
  }

  const templates = collectTemplates(app);
  if (templates.length === 0) {
    return fail("No templates found in _common/templates.");
  }

  const labels = templates.map((item) => item.label);
  const picked = await qa.suggester(labels, templates, "Pick template");
  if (!picked) {
    notice("Cancelled.");
    return;
  }

  try {
    const cliOutput = applyTemplateViaCli(filepaths, picked.templateName);
    notice(
      `Applied '${picked.templateName}' to ${filepaths.length} file(s).`,
      9000,
    );
    if (cliOutput) console.log(cliOutput);
  } catch (error) {
    return fail(error?.message || String(error));
  }
};

function collectTemplates(app) {
  const root = "_common/templates/";
  const templates = [];

  for (const file of app.vault.getMarkdownFiles()) {
    const path = String(file.path || "");
    if (!path.startsWith(root)) continue;

    const rel = path.slice(root.length);
    if (!rel) continue;
    const templateName = rel.replace(/\.md$/i, "");
    templates.push({
      templateName,
      path,
      label: templateName,
    });
  }

  templates.sort((a, b) => a.path.localeCompare(b.path));
  return templates;
}

function collectFilepaths(params, app) {
  const vars = params.variables || {};
  const candidates = [
    params.filepaths,
    params.files,
    params.selectedFiles,
    vars.filepaths,
    vars.files,
    vars.selectedFiles,
    globalThis.__wkbTemplateFilepaths,
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

function applyTemplateViaCli(filepaths, templateName) {
  const { execFileSync } = require("child_process");
  const wkbCandidates = resolveWkbCandidates();
  const args = [
    "vault",
    "template",
    "apply",
    "--template",
    templateName,
    "--files",
    ...filepaths,
  ];

  let lastError = null;
  for (const wkbBin of wkbCandidates) {
    try {
      const output = execFileSync(wkbBin, args, {
        encoding: "utf-8",
        stdio: ["ignore", "pipe", "pipe"],
      });
      return String(output || "").trim();
    } catch (error) {
      const detail = error && error.message ? String(error.message) : "";
      if (/ENOENT/i.test(detail)) {
        lastError = error;
        continue;
      }
      const stderr =
        error && error.stderr ? String(error.stderr).trim() : "";
      const reason = stderr || detail || "unknown error";
      throw new Error(`Template apply failed via '${wkbBin}': ${reason}`);
    }
  }

  const msg =
    (lastError && lastError.message ? String(lastError.message) : "") ||
    "wkb binary not found";
  throw new Error(
    `Template apply failed: unable to locate 'wkb'. Set WKB_BIN env or install wkb on PATH. (${msg})`,
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
