// QuickAdd User Script: build_output_content_fixed.js
// Purpose: No UI. Read `content_index.md`, write `output/output_content.md`.
// Behavior: Pass through all text unchanged EXCEPT replace every Obsidian wikilink
//           ([[Note]], [[Note#Header]], [[Note|Alias]]) with a Markdown link whose
//           link text is literally `content_to_expand` and whose URL is the absolute
//           OS filepath to the target Markdown file. Example: [[Foo|Bar]] →
//           [content_to_expand](/abs/path/to/Foo.md). If a link can't be resolved,
//           leave it as-is.
// Usage: Attach this as a QuickAdd user script. It does not prompt.

module.exports = async (params) => {
  const { app } = params;

  // ---- Constants (hardcoded)
  const INPUT_NOTE = 'content_index.md';
  const OUTPUT_MD  = 'output/output_content.md';

  // ---- Helpers
  const normalizePath = (p) => {
    const adapter = app.vault?.adapter;
    return adapter && adapter.normalizePath
      ? adapter.normalizePath(p)
      : String(p).replace(new RegExp('\\\\', 'g'), '/');
  };

  const ensureFolder = async (filePath) => {
    const np = normalizePath(filePath);
    const parts = np.split('/');
    parts.pop();
    if (!parts.length) return;
    let built = '';
    for (let i = 0; i < parts.length; i++) {
      const seg = parts[i];
      built = built ? built + '/' + seg : seg;
      if (!app.vault.getAbstractFileByPath(built)) {
        await app.vault.createFolder(built);
      }
    }
  };

  const stripMdExt = (p) => (p.slice(-3).toLowerCase() === '.md' ? p.slice(0, -3) : p);
  const wikiRe = /\[\[([^|\]#]+)(?:#[^\]]+)?(?:\|[^\]]+)?\]\]/g; // capture base target only

  const getBasePath = () => {
    const ad = app.vault?.adapter;
    if (ad && typeof ad.getBasePath === 'function') return ad.getBasePath();
    return ad && ad.basePath ? ad.basePath : '';
  };

  const toAbs = (vaultRelPath) => {
    const base = getBasePath();
    if (!base) return vaultRelPath; // fallback to vault-relative if unknown
    return String(base).replace(/[\\\/]$/, '') + '/' + String(vaultRelPath).replace(/^\/+/, '');
  };

  const resolveLink = (rawTarget, fromFile) => {
    if (!rawTarget) return null;
    const mc = app.metadataCache;
    const base = String(rawTarget).trim();
    let dest = mc.getFirstLinkpathDest(base, fromFile?.path || '');
    if (dest && dest.extension) return dest;
    dest = mc.getFirstLinkpathDest(base + '.md', fromFile?.path || '');
    if (dest && dest.extension) return dest;
    const lower = stripMdExt(base).toLowerCase();
    const all = app.vault.getFiles();
    for (let i = 0; i < all.length; i++) {
      const f = all[i];
      const nameNoExt = stripMdExt(f.name).toLowerCase();
      if (nameNoExt === lower) return f;
    }
    return null;
  };

  // ---- Load input note
  const loadInput = async () => {
    const candidates = [INPUT_NOTE, stripMdExt(INPUT_NOTE), INPUT_NOTE.replace(/^\/+/, '')];
    for (const c of candidates) {
      const p = normalizePath(c.endsWith('.md') ? c : c + '.md');
      const f = app.vault.getFileByPath(p);
      if (f) return await app.vault.read(f);
    }
    return null;
  };

  const src = await loadInput();
  if (src == null) {
    if (typeof Notice === 'function') new Notice(`Input not found: ${INPUT_NOTE}`);
    return;
  }

  // ---- Replace wikilinks with absolute filepaths (plain text)
  const replaced = src.replace(wikiRe, (full, target) => {
    try {
      const dest = resolveLink(target, null);
      if (!dest || !dest.path) return full; // leave as-is if missing
      const abs = toAbs(normalizePath(dest.path));
      return `[content_to_expand](${abs})`;
    } catch (e) {
      return full; // conservative: don't mutate on error
    }
  });

  // ---- Write output
  await ensureFolder(OUTPUT_MD);
  await app.vault.adapter.write(normalizePath(OUTPUT_MD), replaced);
  if (typeof Notice === 'function') new Notice(`Wrote → ${OUTPUT_MD}`);
};
