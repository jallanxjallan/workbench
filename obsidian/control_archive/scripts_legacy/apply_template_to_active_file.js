module.exports = async function applyTemplateToActiveFile(params = {}) {
  const shared = loadShared(params);
  const app = shared.resolveApp(params.app);
  const qa = shared.resolveQuickAdd(params);

  if (!app || !app.vault || !app.workspace) {
    return shared.notice("Obsidian context not available.");
  }

  const activeFile = shared.getActiveMarkdownFile(app);
  if (!activeFile) {
    return shared.notice("No active markdown file.");
  }

  let template;
  try {
    template = await shared.pickTemplate(app, qa, "Pick template for active file");
  } catch (error) {
    return shared.notice(`Template selection failed: ${error.message}`);
  }

  const confirmed = await shared.confirmAction(
    qa,
    "Apply template",
    `Apply ${template.file.basename} to ${activeFile.path}?`
  );
  if (!confirmed) {
    return shared.notice("Apply template cancelled.");
  }

  const summary = await shared.applyTemplateToFiles({
    app,
    files: [activeFile],
    template,
  });

  await shared.showSummary(qa, "Template Report", renderSummary(summary));
  return summary;
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

function renderSummary(summary) {
  const lines = [
    `Template: ${summary.template}`,
    `Files processed: ${summary.processed}`,
    `Files updated: ${summary.updated}`,
    `Failures: ${summary.failures.length}`,
  ];

  summary.failures.forEach((failure) => {
    lines.push(`${failure.path}: ${failure.reason}`);
  });

  return lines;
}
