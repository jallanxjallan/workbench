module.exports = async function inspectIngest(params = {}) {
  const shared = loadShared(params);
  const app = shared.resolveApp(params.app);
  const qa = shared.resolveQuickAdd(params);

  if (!app || !app.vault || !app.workspace) {
    return shared.notice("Obsidian context not available.");
  }

  if (!qa || typeof qa.checkboxPrompt !== "function") {
    return shared.notice("Inspect _ingest requires QuickAdd checkboxPrompt support.");
  }

  const ingestFiles = shared.getIngestMarkdownFiles(app);
  if (ingestFiles.length === 0) {
    return shared.notice("No markdown files found in _ingest.");
  }

  let selectedPaths = [];
  try {
    selectedPaths = await qa.checkboxPrompt(
      ingestFiles.map((file) => file.path),
      []
    );
  } catch (_error) {
    return shared.notice("Inspect _ingest cancelled.");
  }

  const files = shared.markdownFilesFromPaths(app, selectedPaths);
  if (files.length === 0) {
    return shared.notice("No _ingest files selected.");
  }

  let template;
  try {
    template = await shared.pickTemplate(app, qa, "Pick template for selected _ingest files");
  } catch (error) {
    return shared.notice(`Template selection failed: ${error.message}`);
  }

  const confirmed = await shared.confirmAction(
    qa,
    "Inspect _ingest",
    `Apply ${template.file.basename} to ${files.length} selected _ingest file(s)?`
  );
  if (!confirmed) {
    return shared.notice("Inspect _ingest cancelled.");
  }

  const summary = await shared.applyTemplateToFiles({
    app,
    files,
    template,
  });

  await shared.showSummary(qa, "Import Report", renderSummary(summary));
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
