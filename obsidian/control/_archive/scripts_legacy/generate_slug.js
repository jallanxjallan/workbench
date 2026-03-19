module.exports = async function generateSlug(params = {}) {
  const shared = loadShared(params);
  const app = shared.resolveApp(params.app);
  if (!app || !app.vault || !app.workspace) {
    throw new Error("Obsidian context not available.");
  }

  const file = params.file || shared.getActiveMarkdownFile(app);
  if (!file) {
    throw new Error("No markdown file available for slug generation.");
  }

  return shared.buildSlugForFile(app, file);
};

function loadShared(params = {}) {
  const path = require("path");
  const app = params.app || globalThis.app || (typeof window !== "undefined" ? window.app : null);
  const adapter = app?.vault?.adapter;
  const basePath =
    (adapter && typeof adapter.getBasePath === "function" && adapter.getBasePath()) ||
    adapter?.basePath;
  if (!basePath) {
    throw new Error("vault base path is unavailable");
  }
  return require(path.join(String(basePath), "_common", "scripts", "_shared.js"));
}
