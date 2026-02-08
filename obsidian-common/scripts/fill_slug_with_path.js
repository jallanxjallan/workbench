module.exports = (quickAddApi, [path]) => {
  const toKebab = (s) =>
    String(s || "")
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .replace(/-{2,}/g, "-");

  if (!path) {
    console.error("No path provided to the slug helper script.");
    return "";
  }

  // Split the provided path, not the active file's path
  const parts = path.split("/");
  const parent = parts.length > 1 ? parts[parts.length - 2] : "";
  const base = parts[parts.length - 1].replace(/\.md$/i, "");

  const slug = parent ? `${toKebab(parent)}-${toKebab(base)}` : toKebab(base);
  
  // Return the slug so the template can insert it.
  return slug;
};
