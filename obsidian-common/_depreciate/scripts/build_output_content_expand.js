// QuickAdd User Script: build_output_content_expand.js
// Purpose: No UI. Read `content_index.md`, write `output/output_content.md`.
// Behavior: For any *paragraph* that contains one or more Obsidian wikilinks
//           ([[Note]], [[Note#Header]], [[Note|Alias]]), REPLACE THE ENTIRE
//           PARAGRAPH with the concatenated body text of the linked note(s).
//           Body text extraction rule: take content *after* YAML frontmatter
//           and *up to (but not including)* the first horizontal rule line; if
//           no horizontal rule exists, take the entire remaining body.
//           Paragraphs without wikilinks are passed through unchanged.
//           If a link cannot be resolved, that link is ignored; if none in a
//           paragraph resolve, the paragraph is left as-is.
// Usage: Attach as a QuickAdd user script. It does not prompt.

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

  // Capture the *base* target only (ignore #heading and |alias)
  const wikiReGlobal = /\[\[([^|\]#]+)(?:#[^\]]+)?(?:\|[^\]]+)?\]\]/g;
  const wikiReTest   = /\[\[[^\]]+\]\]/; // quick test: does a paragraph contain *any* wikilink?

  const resolveLink = (rawTarget, fromFile) => {
    if (!rawTarget) return null;
    const mc = app.metadataCache;
    const base = String(rawTarget).trim();
    let dest = mc.getFirstLinkpathDest(base, fromFile?.path || '');
    if (dest && dest.extension) return dest;
    dest = mc.getFirstLinkpathDest(base + '.md', fromFile?.path || '');
    if (dest && dest.extension) return dest;
    // Fallback: case-insensitive scan across vault
    const lower = stripMdExt(base).toLowerCase();
    const all = app.vault.getFiles();
    for (let i = 0; i < all.length; i++) {
      const f = all[i];
      const nameNoExt = stripMdExt(f.name).toLowerCase();
      if (nameNoExt === lower) return f;
    }
    return null;
  };

  const loadInput = async () => {
    const candidates = [INPUT_NOTE, stripMdExt(INPUT_NOTE), INPUT_NOTE.replace(/^\/+/, '')];
    for (const c of candidates) {
      const p = normalizePath(c.endsWith('.md') ? c : c + '.md');
      const f = app.vault.getFileByPath(p);
      if (f) return await app.vault.read(f);
    }
    return null;
  };

  // Extract body: after YAML frontmatter, up to first horizontal rule; else full body
  const extractBody = (raw) => {
    if (raw == null) return '';
    let text = String(raw);

    // Normalize line endings
    text = text.replace(/\r\n?/g, '\n');

    let idx = 0;
    if (text.startsWith('---\n')) {
      const fmEnd = text.indexOf('\n---\n', 4);
      if (fmEnd !== -1) {
        idx = fmEnd + 5; // position *after* the newline before closing --- ("\n---\n")
      }
    }
    let body = text.slice(idx);

    // Find first horizontal rule line in body (---, *** or ___ on its own line with optional spaces)
    const hrMatch = body.match(/^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/m);
    if (hrMatch) {
      const cut = hrMatch.index;
      body = body.slice(0, cut);
    }

    return body.trim();
  };

  // Expand a paragraph by replacing it with concatenated linked note bodies
  const expandParagraph = async (para, fromFile) => {
    const links = [];
    for (const m of para.matchAll(wikiReGlobal)) {
      const target = m[1];
      if (target && !links.includes(target)) links.push(target);
    }
    const chunks = [];
    for (const t of links) {
      const dest = resolveLink(t, fromFile);
      if (!dest) continue;
      try {
        const raw = await app.vault.read(dest);
        const body = extractBody(raw);
        if (body) chunks.push(body);
      } catch (e) {
        // ignore failures for individual links
      }
    }
    // If at least one link expanded, return concatenated content; else original paragraph
    return chunks.length ? chunks.join('\n\n') : para;
  };

  // ---- Main
  const src = await loadInput();
  if (src == null) {
    if (typeof Notice === 'function') new Notice(`Input not found: ${INPUT_NOTE}`);
    return;
  }

  // Split into paragraphs (blocks separated by one or more blank lines). Keep simple join with two newlines.
  const normalized = src.replace(/\r\n?/g, '\n');
  const paragraphs = normalized.split(/\n{2,}/);

  const outParas = [];
  for (let i = 0; i < paragraphs.length; i++) {
    const para = paragraphs[i];
    if (wikiReTest.test(para)) {
      outParas.push(await expandParagraph(para, null));
    } else {
      outParas.push(para);
    }
  }

  const out = outParas.join('\n\n');

  await ensureFolder(OUTPUT_MD);
  await app.vault.adapter.write(normalizePath(OUTPUT_MD), out);
  if (typeof Notice === 'function') new Notice(`Wrote → ${OUTPUT_MD}`);
};