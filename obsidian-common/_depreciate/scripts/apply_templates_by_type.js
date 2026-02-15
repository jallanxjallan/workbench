// apply_templates_by_type.js — Batch-apply template metadata by `type`
// • Scans the vault for Markdown files, skipping "_common/".
// • Only processes files with status === "🔳".
// • Loads `_common/templates/<type>.md` and merges missing metadata keys.
// • slug: kebab(parentFolder-basename)
// • uid: timestamp + random 3 digits
// • No UI prompts; concise notice at end.

module.exports = async (tp) => {
  const { app, TFile } = window;
  const INBOX = "🔳";
  const COMMON_ROOT = "_common/";

  // Helpers -------------------------------------------------------------
  const isMd = (f) => f && f.extension === "md";
  const isManagedAsset = (f) =>
    f.path.startsWith(COMMON_ROOT) ||
    f.path.startsWith("_depreciate/");

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

  const cloneValue = (value) => JSON.parse(JSON.stringify(value));
  const isPlainObject = (value) =>
    Object.prototype.toString.call(value) === "[object Object]";
  const isEmptyValue = (value) =>
    value === undefined ||
    value === null ||
    value === "" ||
    (Array.isArray(value) && value.length === 0);

  const readTemplateMeta = async (tfile) => {
    const cached = app.metadataCache.getFileCache(tfile)?.frontmatter;
    if (cached && typeof cached === "object") {
      const meta = cloneValue(cached);
      delete meta.position;
      return meta;
    }

    const text = await app.vault.read(tfile);
    const parseYaml = globalThis?.obsidian?.parseYaml;
    const m = /^---\n([\s\S]*?)\n---/m.exec(text);
    if (!m) return {};
    if (typeof parseYaml === "function") {
      try {
        const parsed = parseYaml(m[1]);
        if (parsed && typeof parsed === "object") return parsed;
      } catch (_) {
        // Fall through to minimal parser.
      }
    }

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

  const mergeMissing = (target, source) => {
    let changed = false;
    for (const [key, sourceValue] of Object.entries(source || {})) {
      const targetValue = target[key];
      if (isPlainObject(sourceValue)) {
        if (isEmptyValue(targetValue) || !isPlainObject(targetValue)) {
          target[key] = cloneValue(sourceValue);
          changed = true;
        } else if (mergeMissing(targetValue, sourceValue)) {
          changed = true;
        }
        continue;
      }

      if (isEmptyValue(targetValue)) {
        target[key] = cloneValue(sourceValue);
        changed = true;
      }
    }
    return changed;
  };

  // Main ---------------------------------------------------------------
  const files = app.vault.getMarkdownFiles().filter((f) => isMd(f) && !isManagedAsset(f));
  if (!files.length) {
    new Notice("No markdown files found outside _common/.");
    return;
  }

  let updated = 0, skippedNoType = 0, skippedNoTemplate = 0, skippedStatus = 0;

  for (const f of files) {
    const fm = getFrontmatter(f);
    if (fm.status !== INBOX) { skippedStatus++; continue; }

    const noteType = (fm && typeof fm.type === "string") ? fm.type.trim() : "";
    if (!noteType) { skippedNoType++; continue; }

    const templatePath = `${COMMON_ROOT}templates/${noteType}.md`;
    const t = app.vault.getAbstractFileByPath(templatePath);
    if (!t || !(t instanceof TFile)) { skippedNoTemplate++; continue; }

    const tmeta = await readTemplateMeta(t);
    const templateMeta = cloneValue(tmeta || {});
    delete templateMeta.position;
    delete templateMeta.slug;

    let changed = false;
    await app.fileManager.processFrontMatter(f, (liveFm) => {
      if (mergeMissing(liveFm, templateMeta)) changed = true;
      if (isEmptyValue(liveFm.slug)) {
        liveFm.slug = computeSlugFor(f);
        changed = true;
      }
      if (isEmptyValue(liveFm.uid)) {
        liveFm.uid = ts();
        changed = true;
      }
    });

    if (changed) updated++;
  }

  new Notice(`Templates applied: ${updated} updated; skipped — ${skippedStatus} status≠${INBOX}, ${skippedNoType} no type, ${skippedNoTemplate} missing template.`);
};
