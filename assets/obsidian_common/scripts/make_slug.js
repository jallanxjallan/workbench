// make_slug.js — Replace slug placeholder in active note via `wkb slug`.
// Rules:
// - Slug logic lives in Python only.
// - Calls: wkb slug "<folder>" "<filename>"
// - Replaces: slug: __SLUG__
const { notice, makeFail, buildSlugViaCli } = require("./_shared");

const fail = makeFail("make_slug");

module.exports = async function makeSlug(params = {}) {
  const app = params.app || globalThis.app;
  if (!app || !app.vault) return fail("Obsidian app context not available.");

  const activeFile = app.workspace && app.workspace.getActiveFile
    ? app.workspace.getActiveFile()
    : null;
  if (!activeFile) return fail("No active file.");
  if (activeFile.extension !== "md") return fail("Active file must be markdown.");

  const text = await app.vault.read(activeFile);
  const slug = buildSlugViaCli(app, activeFile);
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
