function notice(message, timeout = 8000) {
  if (typeof Notice === "function") new Notice(message, timeout);
  console.log(message);
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

function buildSlugViaCli(app, activeFile) {
  const { execFileSync } = require("child_process");
  const path = require("path");
  const fullPath = resolveFileAbsolutePath(app, activeFile);
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

module.exports = {
  notice,
  makeFail,
  isDataviewQueryNote,
  getVaultBasePath,
  resolveFileAbsolutePath,
  buildSlugViaCli,
};
