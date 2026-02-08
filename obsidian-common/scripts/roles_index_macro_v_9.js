// QuickAdd User Script — Instructions indexer (DICT of FLAT values, wikilinks resolved)
// Schema v10: Local‑over‑Remote override semantics ("Python subclassing" style)
//
// What’s new vs v9
//   1) Override policy for duplicate slugs and ambiguous link matches:
//        - Prefer files in the *calling vault* ("local") over those in the
//          symlinked common vault ("remote").
//        - You control which folders are considered "remote" via REMOTE_ROOTS.
//        - When two files define the same slug, the LOCAL one wins and the
//          REMOTE is silently shadowed (recorded in a note footer summary).
//   2) Link resolution preference uses the same policy: on basename/path
//      collisions, prefer LOCAL.
//   3) Keeps all other behavior: outputs a flat JSON keyed by slug with
//      { slug, file (abs), vaultlink (no .md), mtime (UNIX s), ...frontmatter }
//      and normalizes `inherits` to an array of slugs.

module.exports = async (params) => {
  const { app } = params;

  // --- Settings ----------------------------------------------------------
  const INDEX_JSON     = 'index/instructions_index.json';
  const INDEX_NOTE     = 'index/Instructions Index.md';

  // Mark any vault‑relative *top‑level folders* that are symlinked remotes.
  // Everything *not* under these roots is treated as LOCAL and has priority.
  // Example: your calling vault contains a folder named `common/` that is a
  // symlink to another vault. Then: REMOTE_ROOTS = ['common']
  const REMOTE_ROOTS = ['common'];

  // --- Helpers -----------------------------------------------------------
  const normalizePath = (p) => {
    const adapter = app.vault?.adapter;
    return adapter && adapter.normalizePath ? adapter.normalizePath(p) : String(p).replace(/\/g, '/');
  };

  const ensureFolder = async (filePath) => {
    const np = normalizePath(filePath);
    const parts = np.split('/');
    parts.pop();
    let built = '';
    for (const seg of parts) {
      built = built ? built + '/' + seg : seg;
      if (!app.vault.getAbstractFileByPath(built)) {
        await app.vault.createFolder(built);
      }
    }
  };

  const toArray = (v) => (v == null ? [] : Array.isArray(v) ? v : [v]);
  const stripMdExt = (p) => (p.slice(-3).toLowerCase() === '.md' ? p.slice(0, -3) : p);
  const basenameNoExt = (p) => stripMdExt(p.split('/').pop());

  // Obsidian‑friendly wikilink for the note view (vault‑relative, no .md)
  const asVaultWiki = (path) => '[[' + stripMdExt(path) + ']]';

  const pathRank = (vaultRelPath) => {
    // Lower is better. 0 = LOCAL, 1 = REMOTE, 2 = unknown fallback.
    const p = String(vaultRelPath || '');
    for (let i = 0; i < REMOTE_ROOTS.length; i++) {
      const root = REMOTE_ROOTS[i];
      if (!root) continue;
      if (p === root || p.startsWith(root + '/')) return 1; // remote
    }
    return 0; // local (default)
  };

  const preferLocal = (a, b) => pathRank(a.path) - pathRank(b.path);

  // --- Link parsing / resolution ----------------------------------------
  const mdExtRe = /\.?md$/i;
  const wikiRe  = /^\[\[([^|\]#]+)(?:#[^\]]+)?\]\]$/;

  const isAbsoluteFsPath = (s) => typeof s === 'string' && /^(?:\/?[A-Za-z]:\|\/?[A-Za-z]:\/|\/|~\/)/.test(s);

  const parseObsidianUrl = (s) => {
    // obsidian://open?vault=Name&file=Folder%2FNote
    try {
      if (typeof s !== 'string' || !s.startsWith('obsidian://')) return null;
      const u = new URL(s);
      const file = u.searchParams.get('file');
      if (!file) return null;
      return decodeURIComponent(file).replace(/^\/+/, '');
    } catch (_) {
      return null;
    }
  };

  const extractLinkText = (raw) => {
    if (raw && typeof raw === 'object') {
      if (raw.path) return String(raw.path).replace(mdExtRe, '');
      if (raw.link) return extractLinkText(String(raw.link));
    }
    if (typeof raw !== 'string') return null;
    const s = raw.trim();
    const fromObsidian = parseObsidianUrl(s);
    if (fromObsidian) return stripMdExt(fromObsidian);
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
          if (!/templates/.test(pathLower)) stack.push(child);
        } else if (isFile(child) && child.extension === 'md') {
          const pathLower = String(child.path || '').toLowerCase();
          if (!pathLower.includes('/templates/')) files.push(child);
        }
      }
    }
    files.sort((a, b) => a.path.localeCompare(b.path));
    return files;
  };

  const allFiles = gatherAllMarkdownFiles();

  // indices for fallback matching (case‑insensitive)
  const byVaultRelNoExt = new Map(); // 'folder/name' (no .md) → file
  const byBasenameNoExt = new Map(); // 'name' → [files]
  for (const f of allFiles) {
    const noext = stripMdExt(f.path);
    const key1 = noext.toLowerCase();
    const key2 = basenameNoExt(noext).toLowerCase();
    // for exact vault‑relative, keep the *best* according to preferLocal
    const prev = byVaultRelNoExt.get(key1);
    if (!prev || preferLocal(f, prev) < 0) byVaultRelNoExt.set(key1, f);
    // for basename, keep a list sorted by preference
    const arr = byBasenameNoExt.get(key2) || [];
    arr.push(f);
    arr.sort(preferLocal);
    byBasenameNoExt.set(key2, arr);
  }

  const getCache = (file) => app.metadataCache.getFileCache(file) || {};
  const getFM    = (file) => getCache(file).frontmatter || {};

  const deepClone = (obj) => JSON.parse(JSON.stringify(obj || {}));

  const targetSlugFromFile = (file) => {
    if (!file) return null;
    const fm = getFM(file) || {};
    if (fm && fm.slug) return String(fm.slug).trim();
    return basenameNoExt(file.path);
  };

  const problems = [];
  const overrides = [];

  const resolveLink = (raw, srcFile) => {
    const base = extractLinkText(raw);
    if (!base) return null;
    const mc = app.metadataCache;

    // 1) Normal Obsidian resolution
    let dest = tryResolve(mc, base, srcFile.path);
    if (dest) return dest;

    // 2) Absolute path → basename match w/ preference
    if (isAbsoluteFsPath(base)) {
      const tail = basenameNoExt(base).toLowerCase();
      const candidates = byBasenameNoExt.get(tail) || [];
      if (candidates.length >= 1) return candidates[0];
    }

    // 3) Direct vault‑relative lookup (no .md)
    const norm = base.replace(/^\/+/, '').toLowerCase();
    if (byVaultRelNoExt.has(norm)) return byVaultRelNoExt.get(norm);

    // 4) Basename fallback (prefer LOCAL)
    const lower = basenameNoExt(base).toLowerCase();
    const arr = byBasenameNoExt.get(lower) || [];
    if (arr.length >= 1) return arr[0];

    return null;
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
      } else {
        problems.push(`Unresolved inherits link in ${srcFile.path}: ${JSON.stringify(raw)}`);
      }
    }
    return out;
  };

  const toUnixSeconds = (ms) => Math.floor(Number(ms || 0) / 1000);
  const formatDate = (unixSeconds) => new Date(unixSeconds * 1000).toISOString().replace('T', ' ').replace(/\..+$/, '');

  // --- Build rows first (allow duplicates) -------------------------------
  const rows = []; // [{ slug, file, row, rank }]
  for (let i = 0; i < allFiles.length; i++) {
    const file = allFiles[i];
    const fm = getFM(file);
    const slug = (fm.slug == null ? '' : String(fm.slug)).trim();
    if (!slug) continue;

    // Base row: clone FM, drop noisy fields
    const row = deepClone(fm);
    delete row.position;
    delete row.slug;

    row.slug = slug;
    row.file = normalizePath(file.path);
    row.vaultlink = stripMdExt(file.path);

    if (fm.inherits != null) row.inherits = normalizeLinkListToSlugs(file, fm.inherits);

    const stat = await app.vault.adapter.stat(file.path);
    row.mtime = toUnixSeconds(stat?.mtime || Date.now());

    rows.push({ slug, file, row, rank: pathRank(file.path) });
  }

  // --- Apply LOCAL‑over‑REMOTE preference by slug ------------------------
  const grouped = new Map(); // slug → [rows]
  for (const r of rows) {
    const arr = grouped.get(r.slug) || [];
    arr.push(r);
    grouped.set(r.slug, arr);
  }

  const index = {}; // final slug → row
  const slugs = Array.from(grouped.keys());
  for (const slug of slugs) {
    const candidates = grouped.get(slug).sort((a, b) => a.rank - b.rank);
    const picked = candidates[0]; // LOCAL wins (rank 0 < 1)
    index[slug] = picked.row;
    // Record any shadowed remotes for the note footer
    for (let i = 1; i < candidates.length; i++) {
      const c = candidates[i];
      if (c.rank > picked.rank) {
        overrides.push(`${slug}: ${picked.file.path} overrides ${c.file.path}`);
      }
    }
  }

  if (problems.length) {
    // Non‑fatal: include in footer instead of throwing, so overrides can apply.
    // If you want to enforce hard failures, switch back to throw.
    // throw new Error(["Validation errors detected:", problems.join("
")].join("

"));
  }

  // --- Output JSON -------------------------------------------------------
  const jsonPayload = JSON.stringify(index, null, 2);
  await ensureFolder(INDEX_JSON);
  await app.vault.adapter.write(normalizePath(INDEX_JSON), jsonPayload);

  // --- Human‑readable index note ----------------------------------------
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
    if (row.vaultlink) lines.push('- Source: ' + asVaultWiki(row.vaultlink));
    lines.push('- Absolute: `' + row.file + '`');
    if (row.label) lines.push('- Label: `' + row.label + '`');
    if (row.title) lines.push('- Frontmatter Title: ' + row.title);
    if (row.mtime) lines.push('- Updated: ' + formatDate(row.mtime));
    if (row.inherits && row.inherits.length) {
      lines.push('- Inherits (slugs):');
      for (let i = 0; i < row.inherits.length; i++) lines.push('  - ' + row.inherits[i]);
    }
    lines.push('');
  }

  if (overrides.length || problems.length) {
    lines.push('---');
    if (overrides.length) {
      lines.push('**Overrides (local → remote):**');
      for (const s of overrides) lines.push('- ' + s);
      lines.push('');
    }
    if (problems.length) {
      lines.push('**Unresolved / Notes:**');
      for (const s of problems) lines.push('- ' + s);
      lines.push('');
    }
  }

  const noteContent = lines.join('
').replace(/
+$/, '') + '
';
  await ensureFolder(INDEX_NOTE);
  await app.vault.adapter.write(normalizePath(INDEX_NOTE), noteContent);

  if (typeof Notice === 'function') new Notice('Indexed ' + Object.keys(index).length + ' notes (local overrides applied) → ' + INDEX_JSON);
};
