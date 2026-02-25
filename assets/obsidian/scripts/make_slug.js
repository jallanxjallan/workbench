// make_slug.js — Replace slug placeholder in active note via `wkb slug`.
// Rules:
// - Slug logic lives in Python only.
// - Calls: wkb slug "<folder>" "<filename>"
// - Replaces: slug: __SLUG__

module.exports = async function makeSlug(params = {}) {
  const app = params.app || globalThis.app;
  if (!app || !app.vault) return fail("Obsidian app context not available.");

  const activeFile = app.workspace && app.workspace.getActiveFile
    ? app.workspace.getActiveFile()
    : null;
  if (!activeFile) return fail("No active file.");
  if (activeFile.extension !== "md") return fail("Active file must be markdown.");

  const text = await app.vault.read(activeFile);
  const slug = callSlugCli(app, activeFile);
  const updated = replaceSlugPlaceholder(text, slug);
  if (updated === text) {
    return fail("Placeholder `slug: __SLUG__` not found.");
  }

  await app.vault.modify(activeFile, updated);
  notice(`Slug set: ${slug}`);
};

function replaceSlugPlaceholder(text, slug) {
  return String(text || "").replace(
    /^(\s*slug:\s*)__SLUG__(\s*)$/m,
    (_, prefix, suffix) => `${prefix}${slug}${suffix}`,
  );
}

function callSlugCli(app, activeFile) {
  const { execFileSync } = require("child_process");
  const path = require("path");
  const fullPath = resolveFullPath(app, activeFile);
  const folderPath = path.dirname(fullPath);
  const filename = path.basename(fullPath);
  const wkbBin = process.env.WKB_BIN || "wkb";

  try {
    const output = execFileSync(wkbBin, ["slug", folderPath, filename], {
      encoding: "utf-8",
      stdio: ["ignore", "pipe", "pipe"],
    });
    const slug = String(output || "").trim();
    if (!slug) throw new Error("empty slug from CLI");
    return slug;
  } catch (error) {
    const stderr = error && error.stderr ? String(error.stderr).trim() : "";
    const detail = stderr || (error && error.message ? error.message : "unknown error");
    throw new Error(`slug generation failed via '${wkbBin} slug': ${detail}`);
  }
}

function resolveFullPath(app, activeFile) {
  const adapter = app.vault && app.vault.adapter;
  const basePath =
    (adapter && typeof adapter.getBasePath === "function" && adapter.getBasePath()) ||
    (adapter && adapter.basePath) ||
    "";
  if (!basePath) throw new Error("vault base path is unavailable");
  const path = require("path");
  return path.join(basePath, String(activeFile.path || ""));
}

function notice(message, timeout = 8000) {
  if (typeof Notice === "function") new Notice(message, timeout);
  console.log(message);
}

function fail(message) {
  const text = `make_slug failed: ${message}`;
  if (typeof Notice === "function") new Notice(text, 10000);
  console.error(text);
}
