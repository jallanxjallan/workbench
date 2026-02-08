// QuickAdd User Script — Instructions indexer (DICT of FLAT values, wikilinks resolved)
// Schema v7: index ALL markdown notes (except any under a `templates` folder)
// that contain a `slug` in frontmatter. Output is a *flat JSON object* keyed
// by slug. Each value is a flat dict with only top‑level fields — no nested dicts.
// Keys included: `slug`, `file` (absolute), `mtime` (UNIX seconds), plus all
// frontmatter keys (except `position` and duplicate `slug`).
// `inherits` is resolved: any wikilinks are converted to the target file's slug.
// The markdown index note shows a human‑readable updated date.

module.exports = async (params) => {
  const { app } = params;

  // --- Settings ----------------------------------------------------------
  const INDEX_JSON     = 'index/instructions_index.json';
  const INDEX_NOTE     = 'index/Instructions Index.md';

  // --- Helpers -----------------------------------------------------------
  const normalizePath = (p) => {
    const adapter = app.vault?.adapter;
    return adapter && adapter.normalizePath ? adapter.normalizePath(p) : String(p).replace(new RegExp('\\\\','g'), '/');
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

  const toArray = (v) => (v == null ? [] : Array.isArray(v) ? v : [v]);
  const stripMdExt = (p) => (p.slice(-3) === '.md' ? p.slice(0, -3) : p);
  const basenameNoExt = (p) => stripMdExt(p.split('/').pop());
  const asWiki = (path) => '[[' + stripMdExt(path) + ']]';

  const mdExtRe   = new RegExp('\n?\\.md$', 'i');
  // Use a safe regex literal (avoid escaping hell in new RegExp)
const wikiRe = /^\[\[([^|\]#]+)(?:#[^\]]+)?\]\]$/;

  const extractLinkText = (raw) => {
    if (raw && typeof raw === 'object') {
      if (raw.path) return String(raw.path).replace(mdExtRe, '');
      if (raw.link) return extractLinkText(String(raw.link));
    }
    if (typeof raw !== 'string') return null;
    const s = raw.trim();
    const m = wikiRe.exec(s);
    if (m) return m[1];
    return s.replace(mdExtRe, '');
  };

  const tryResolve = (mc, target, from) => {
    let d = mc.getFirstLinkpathDest(target, from);
    if (d && d.extension) return d;
    d = mc.getFirstLinkpathDest(target + '.md', from);
    return d && d.extension ? d : null;
  };

  const resolveLink = (raw, srcFile) => {
    const base = extractLinkText(raw);
    if (!base) return null;
    const mc = app.metadataCache;

    let dest = tryResolve(mc, base, srcFile.path);
    if (dest) return dest;

    const all = app.vault.getFiles();
    const lower = base.toLowerCase();
    for (let i = 0; i < all.length; i++) {
      const f = all[i];
      const noext = stripMdExt(f.path).toLowerCase();
      const nameNoExt = stripMdExt(f.name).toLowerCase();
      if (noext.endsWith('/' + lower) || nameNoExt === lower) return f;
    }
    return null;
  };

  const isFolder = (abs) => abs && typeof abs === 'object' && Array.isArray(abs.children);
  const isFile   = (abs) => abs && typeof abs === 'object' && typeof abs.extension === 'string';

  const gatherAllMarkdownFiles = () => {
    const root = app.vault.getRoot();
    const files = [];
    const stack = [root];
    while (stack.length) {
      const cur = stack.pop();
      if (!cur || !cur.children) continue;
      for (let i = 0; i < cur.children.length; i++) {
        const child = cur.children[i];
        if (isFolder(child)) {
          const pathLower = String(child.path || '').toLowerCase();
          if (!/\btemplates\b/.test(pathLower)) stack.push(child);
        } else if (isFile(child) && child.extension === 'md') {
          const pathLower = String(child.path || '').toLowerCase();
          if (!pathLower.includes('/templates/')) files.push(child);
        }
      }
    }
    files.sort((a, b) => a.path.localeCompare(b.path));
    return files;
  };

  const getCache = (file) => app.metadataCache.getFileCache(file) || {};
  const getFM    = (file) => getCache(file).frontmatter || {};

  const deepClone = (obj) => JSON.parse(JSON.stringify(obj || {}));

  const targetSlugFromFile = (file) => {
    if (!file) return null;
    const fm = getFM(file) || {};
    if (fm && fm.slug) return String(fm.slug).trim();
    return basenameNoExt(file.path);
  };

  const normalizeLinkListToSlugs = (srcFile, listLike) => {
    const arr = toArray(listLike);
    const out = [];
    for (let i = 0; i < arr.length; i++) {
      const raw = arr[i];
      const dest = resolveLink(raw, srcFile);
      if (dest) {
        const s = targetSlugFromFile(dest);
        if (s) out.push(s);
      } else if (typeof raw === 'string' && raw.trim()) {
        const cleaned = extractLinkText(raw);
        if (cleaned) out.push(cleaned);
      }
    }
    return [...new Set(out)];
  };

  const getFileMtime = async (file) => {
    try {
      const stat = await app.vault.adapter.stat(file.path);
      return stat && stat.mtime ? Math.floor(stat.mtime / 1000) : null;
    } catch (e) {
      return null;
    }
  };

  const formatDate = (ts) => {
    try {
      return new Date(ts * 1000).toISOString().slice(0, 19).replace('T', ' ');
    } catch {
      return String(ts);
    }
  };

  // --- Core --------------------------------------------------------------
  const problems = [];
  const index = {}; // keyed by slug

  const files = gatherAllMarkdownFiles();
  const seen = new Set();
  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    const fm = getFM(file);
    const slug = (fm.slug == null ? '' : String(fm.slug)).trim();
    if (!slug) continue;

    if (seen.has(slug)) {
      problems.push("Duplicate slug '" + slug + "' in another file; skipping " + file.path);
      continue;
    }

    const fullFM = deepClone(fm);
    if (typeof fullFM.position !== 'undefined') delete fullFM.position;

    // Normalize inherits → array of slugs (resolved)
    const inheritsSlugs = normalizeLinkListToSlugs(file, fullFM.inherits ?? []);
    if (inheritsSlugs.length) fullFM.inherits = inheritsSlugs; else delete fullFM.inherits;

    const mtime = await getFileMtime(file);

    // Build a flat dict
    const row = Object.assign({}, fullFM);
    delete row.slug;
    row.slug = slug;

    // Absolute path
    const basePath = app.vault?.adapter?.getBasePath?.() || "";
    const toAbs = (p) => basePath ? String(basePath).replace(/[\\\\\/]+$/, "") + "/" + String(p).replace(/^\/+/, "") : p;
    row.file = toAbs(file.path);

    row.mtime = mtime;

    index[slug] = row;
    seen.add(slug);
  }

  if (problems.length) {
    throw new Error(["Validation errors detected:", problems.join("\n")].join("\n\n"));
  }

  // --- Output JSON -------------------------------------------------------
  const jsonPayload = JSON.stringify(index, null, 2);
  await ensureFolder(INDEX_JSON);
  await app.vault.adapter.write(normalizePath(INDEX_JSON), jsonPayload);

  // --- Human-readable note ----------------------------------------------
  const lines = ['# Instructions Index', ''];
  const slugsSorted = Object.keys(index).sort();
  for (const slug of slugsSorted) {
    const row = index[slug];
    const heading = row.title ? String(row.title) : basenameNoExt(row.file);
    lines.push('## ' + heading);
    lines.push('Slugline:');
    lines.push('');
    lines.push('```text');
    lines.push(row.slug);
    lines.push('```');
    lines.push('- Source: ' + asWiki(row.file));
    if (row.label) lines.push('- Label: `' + row.label + '`');
    if (row.title) lines.push('- Frontmatter Title: ' + row.title);
    if (row.mtime) lines.push('- Updated: ' + formatDate(row.mtime));
    if (row.inherits && row.inherits.length) {
      lines.push('- Inherits (slugs):');
      for (let i = 0; i < row.inherits.length; i++) lines.push('  - ' + row.inherits[i]);
    }
    lines.push('');
  }

  const noteContent = lines.join('\n').replace(new RegExp('\n+$'), '') + '\n';
  await ensureFolder(INDEX_NOTE);
  await app.vault.adapter.write(normalizePath(INDEX_NOTE), noteContent);

  if (typeof Notice === 'function') new Notice('Indexed ' + Object.keys(index).length + ' notes with slugs → ' + INDEX_JSON);
};
