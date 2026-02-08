// insert_slug.js — Templater user script
// Map: tp.user.insert_slug({ prefixFolder: true|false })

module.exports = async (tp, opts = {}) => {
  const { prefixFolder = true } = opts;

  const toKebab = (s) =>
    String(s || "")
      .normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
      .trim().toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .replace(/-{2,}/g, "-");

  const title = tp.file.title || "untitled";
  const folder = prefixFolder ? (tp.file.folder(true) || "") : "";
  const base = folder ? `${folder}-${title}` : title;

  return toKebab(base);
};

