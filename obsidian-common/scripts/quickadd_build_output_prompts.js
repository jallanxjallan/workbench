// QuickAdd User Script: build_output_prompts.js
// Hard-coded: scan vault-root "scenes" folder.
// Include ONLY files whose frontmatter `status` is EXACTLY "⚙️".
// Write results to "output_prompts.json" at the vault root.
// Zero UI except Notices for counts / none-found.

module.exports = async (params) => {
  const { app } = params;

  // ---- Hard-coded config
  const INPUT_FOLDER = "scenes";
  const OUTPUT_JSON  = "output/output_prompts.json";
  const REQUIRED_STATUS = "⚙️"; // exact match, no normalization

  // ---- Utilities
  const normalizePath = (p) => {
    const adapter = app.vault?.adapter;
    return adapter && adapter.normalizePath
      ? adapter.normalizePath(p)
      : String(p).replace(/\\/g, "/");
  };

  const stripMdExt = (p) =>
    (String(p).toLowerCase().endsWith(".md") ? p.slice(0, -3) : p);

  const getBasePath = () => {
    const ad = app.vault?.adapter;
    if (ad && typeof ad.getBasePath === "function") return ad.getBasePath();
    return ad && ad.basePath ? ad.basePath : "";
  };

  const toAbs = (vaultRelPath) => {
    const base = getBasePath();
    if (!base) return vaultRelPath;
    return String(base).replace(/[\\/]+$/, "") + "/" + String(vaultRelPath).replace(/^\/+/, "");
  };

  const isFolder = (n) => n && typeof n === "object" && Array.isArray(n.children);
  const isFile   = (n) => n && typeof n === "object" && typeof n.extension === "string";

  const getCache = (file) => app.metadataCache.getFileCache(file) || {};
  const getFM    = (file) => getCache(file).frontmatter || {};

  // ---- Gather markdown files directly under vault-root /scenes/
  const gatherMarkdownUnderFolder = (folderName) => {
    const root = app.vault.getRoot();
    const targetPrefix = ("/" + normalizePath(folderName).replace(/^\/+/, "") + "/").toLowerCase();
    const wanted = [];
    const stack = [root];

    while (stack.length) {
      const cur = stack.pop();
      if (!cur || !cur.children) continue;
      for (let i = 0; i < cur.children.length; i++) {
        const child = cur.children[i];
        if (isFolder(child)) {
          stack.push(child);
        } else if (isFile(child) && child.extension === "md") {
          const pathLower = ("/" + String(child.path).replace(/^\/+/, "")).toLowerCase();
          if (pathLower.startsWith(targetPrefix)) wanted.push(child);
        }
      }
    }

    wanted.sort((a, b) => a.path.localeCompare(b.path));
    return wanted;
  };

  // ---- Run
  const files = gatherMarkdownUnderFolder(INPUT_FOLDER);
  if (!files.length) {
    if (typeof Notice === "function") new Notice("No markdown files found in 'scenes'.");
    return;
  }

  const FRONTMATTER_RE = /^---\s*\n[\s\S]*?\n---\s*\n?/;
  const HR_LINE_RE     = /^---\s*$/m; // first horizontal rule terminates content

  const results = [];

  for (const f of files) {
    const fm = getFM(f) || {};
    const status = fm.status != null ? String(fm.status).trim() : null;
    if (status !== REQUIRED_STATUS) continue; // EXACT match only

    const uid   = fm.uid   != null ? String(fm.uid)   : null;
    const slug  = fm.slug  != null ? String(fm.slug)  : null;
    const title = fm.title != null ? String(fm.title) : stripMdExt(f.name);
    const tags  = Array.isArray(fm.tags)
      ? fm.tags.map(String)
      : (fm.tags != null ? [String(fm.tags)] : null);

    const raw = await app.vault.read(f);

    // strip frontmatter
    let body = raw;
    const fmMatch = raw.match(FRONTMATTER_RE);
    if (fmMatch && fmMatch.index === 0) body = raw.slice(fmMatch[0].length);

    // Trim to before first HR if present; else whole body
    let content = body.trim();
    const hrMatch = body.match(HR_LINE_RE);
    if (hrMatch) content = body.slice(0, hrMatch.index).trim();

    results.push({
      uid: uid,
      content: content,
      metadata: {
        uid: uid,
        slug: slug,
        status: status,
        tags: tags ?? null,
        title: title,
        type: "scene",
      },
      source: { filepath: toAbs(f.path) },
    });
  }

  // ---- Write JSON (vault root)
  const outPath = normalizePath(OUTPUT_JSON);
  await app.vault.adapter.write(outPath, JSON.stringify(results, null, 2));

  // ---- Notices
  if (typeof Notice === "function") {
    if (results.length === 0) {
      new Notice("No flagged (⚙️) prompts found. Wrote 0 entries → " + outPath);
    } else {
      new Notice(`Wrote ${results.length} prompt(s) with status ⚙️ → ${outPath}`);
    }
  }
};

