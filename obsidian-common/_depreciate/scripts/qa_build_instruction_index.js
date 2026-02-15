// Build instructions index: { slug: absoluteFilePath }
module.exports = async (params) => {
  const { app } = params;                           // ✅ QuickAdd gives you `app`, not `vault`
  const adapter = app.vault.adapter;

  // Where to scan / write
  const SRC_FOLDER = "instructions";
  const OUT_FILE   = "_system/index/instructions.json";

  // Resolve absolute base path (desktop FileSystemAdapter)
  const basePath =
    (typeof adapter.getBasePath === "function" && adapter.getBasePath()) ||
    adapter.basePath || ""; // fallback for older builds

  if (!basePath) {
    new Notice("Unable to resolve vault base path (mobile?). Writing JSON still works, but absolute paths may be empty.");
  }

  // Collect .md files from instructions/
  const files = app.vault.getMarkdownFiles()
    .filter(f => f.path.startsWith(SRC_FOLDER + "/"));

  const index = Object.create(null);
  let skippedNoSlug = 0;

  for (const file of files) {
    const fm = app.metadataCache.getFileCache(file)?.frontmatter;
    const slug = fm?.slug && String(fm.slug).trim();
    if (!slug) { skippedNoSlug++; continue; }

    // Absolute path for value
    const abs = require("path").join(basePath || "", file.path);
    index[slug] = abs;
  }

  // Ensure target folder exists (relative to vault root)
  await ensureFolder(app, OUT_FILE);

  // Write JSON using the vault adapter (path relative to vault root)
  await adapter.write(OUT_FILE, JSON.stringify(index, null, 2));

  new Notice(`Instruction index: ${Object.keys(index).length} entries` +
             (skippedNoSlug ? ` • skipped ${skippedNoSlug} (no slug)` : ""));
};

// Create intermediate folders as needed (vault-relative)
async function ensureFolder(app, filePath) {
  const parts = filePath.split("/").slice(0, -1);
  if (!parts.length) return;
  let cur = "";
  for (const p of parts) {
    cur = cur ? `${cur}/${p}` : p;
    try {
      // throws if exists
      await app.vault.createFolder(cur);
    } catch (_) {
      /* already exists */
    }
  }
}

