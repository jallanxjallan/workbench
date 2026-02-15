// QuickAdd User Script: Copy frontmatter "slug" to clipboard
// Usage: Create a QuickAdd Macro → "User Script" → paste this code.
module.exports = async (params) => {
  const app = params.app;
  const qa = params.quickAddApi; // QuickAdd API

  const file = app.workspace.getActiveFile();
  if (!file) {
    new Notice("No active file.");
    return;
  }

  const cache = app.metadataCache.getFileCache(file);
  const fm = cache?.frontmatter;

  if (!fm || typeof fm.slug !== "string" || !fm.slug.trim()) {
    new Notice('No "slug" found in frontmatter.');
    return;
  }

  const slug = fm.slug.trim();
  await qa.utility.setClipboard(slug);
  new Notice(`Copied slug: ${slug}`);
};

