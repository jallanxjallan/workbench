// apply_templates_by_type.js — Batch-apply template metadata by `type`
// • Scans the vault for Markdown files, skipping "_system/".
// • Only processes files with status === "🔳".
// • Loads `_system/templates/<type>.md` and merges missing metadata keys.
// • slug: kebab(parentFolder-basename)
// • uid: timestamp + random 3 digits
// • No UI prompts; concise notice at end.

module.exports = async (tp) => {
  const { app, TFile } = window;
  const INBOX = "🔳";

  // Helpers -------------------------------------------------------------
  const isMd = (f) => f && f.extension === "md";
  const isSystem = (f) => f.path.startsWith("_system/");

  const toKebab = (s) => String(s || "")
    .normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
    .trim().toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/-{2,}/g, "-");

  const ts = () => {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    const YYYY = d.getFullYear();
    const MM = pad(d.getMonth() + 1);
    const DD = pad(d.getDate());
    const hh = pad(d.getHours());
    const mm = pad(d.getMinutes());
    const ss = pad(d.getSeconds());
    const rand = Math.floor(Math.random() * 900 + 100); // 3 random digits
    return `${YYYY}${MM}${DD}${hh}${mm}${ss}${rand}`;
  };

  const readTemplateMeta = async (tfile) => {
    const text = await app.vault.read(tfile);
    const m = /^---\n([\s\S]*?)\n---/m.exec(text);
    if (!m) return {};
    const yml = m[1];
    const lines = yml.split(/\r?\n/);
    const meta = {};
    let currentKey = null;
    for (const line of lines) {
      if (/^\s*-\s/.test(line) && currentKey) {
        if (!Array.isArray(meta[currentKey])) meta[currentKey] = [];
        meta[currentKey].push(line.replace(/^\s*-\s*/, "").trim());
      } else if (/^\s*([A-Za-z0-9_\-]+):\s*(.*)$/.test(line)) {
        const [, k, vraw] = line.match(/^\s*([A-Za-z0-9_\-]+):\s*(.*)$/);
        currentKey = k;
        const v = vraw === undefined ? "" : vraw.trim();
        if (v === "[]") meta[k] = [];
        else if (v === "true") meta[k] = true;
        else if (v === "false") meta[k] = false;
        else if (v === "null" || v === "~") meta[k] = null;
        else if (/^".*"$/.test(v) || /^'.*'$/.test(v)) meta[k] = v.slice(1, -1);
        else meta[k] = v;
      }
    }
    return meta;
  };

  const computeSlugFor = (file) => {
    const parent = file.parent?.name || "";
    const base = file.basename || "untitled";
    const combined = parent ? `${parent}-${base}` : base;
    return toKebab(combined);
  };

  const getFrontmatter = (file) => app.metadataCache.getFileCache(file)?.frontmatter || {};

  const writeFrontmatter = async (file, patch) => {
    await app.fileManager.processFrontMatter(file, (fm) => {
      for (const [k, v] of Object.entries(patch)) {
        fm[k] = v;
      }
    });
  };

  // Main ---------------------------------------------------------------
  const files = app.vault.getMarkdownFiles().filter((f) => isMd(f) && !isSystem(f));
  if (!files.length) {
    new Notice("No markdown files found outside _system/.");
    return;
  }

  let updated = 0, skippedNoType = 0, skippedNoTemplate = 0, skippedStatus = 0;

  for (const f of files) {
    const fm = getFrontmatter(f);
    if (fm.status !== INBOX) { skippedStatus++; continue; }

    const noteType = (fm && typeof fm.type === "string") ? fm.type.trim() : "";
    if (!noteType) { skippedNoType++; continue; }

    const templatePath = `_system/templates/${noteType}.md`;
    const t = app.vault.getAbstractFileByPath(templatePath);
    if (!t || !(t instanceof TFile)) { skippedNoTemplate++; continue; }

    const tmeta = await readTemplateMeta(t);

    const patch = {};
    for (const [k, v] of Object.entries(tmeta)) {
      if (k === "slug") continue;
      if (fm[k] === undefined || fm[k] === null || (Array.isArray(fm[k]) && fm[k].length === 0) || fm[k] === "") {
        patch[k] = v;
      }
    }

    if (fm.slug === undefined || fm.slug === null || fm.slug === "") {
      patch.slug = computeSlugFor(f);
    }

    if (fm.uid === undefined || fm.uid === null || fm.uid === "") {
      patch.uid = ts();
    }

    if (Object.keys(patch).length) {
      await writeFrontmatter(f, patch);
      updated++;
    }
  }

  new Notice(`Templates applied: ${updated} updated; skipped — ${skippedStatus} status≠${INBOX}, ${skippedNoType} no type, ${skippedNoTemplate} missing template.`);
};

