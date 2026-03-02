function notice(message, timeout = 8000) {
  if (typeof Notice === "function") new Notice(message, timeout);
  console.log(message);
}

function fail(message) {
  const text = `Toggle Image Visibility failed: ${message}`;
  if (typeof Notice === "function") new Notice(text, 10000);
  console.error(text);
}

const THUMB_WIDTH = 240;

module.exports = async function toggleImageVisibility(params = {}) {
  const app = params.app || globalThis.app;
  if (!app || !app.vault || !app.metadataCache) {
    return fail("Obsidian app context not available.");
  }

  const activeFile = app.workspace?.getActiveFile?.();
  if (!activeFile) return fail("No active file.");
  if (activeFile.extension !== "md") return fail("Active file must be markdown.");
  if (!isContentPath(activeFile.path)) {
    return fail("Active file must be inside /content or /contents.");
  }

  const fileCache = app.metadataCache.getFileCache(activeFile) || {};
  const frontmatter = normalizeFrontmatter(fileCache.frontmatter);
  const type = String(frontmatter.type || "").trim().toLowerCase();
  if (type !== "image") {
    return fail("Active file is not type: image.");
  }

  const raw = await app.vault.read(activeFile);
  const { head, body } = splitNote(raw);

  if (hasLeadingImageLink(body)) {
    const nextBody = removeLeadingImageLink(body);
    await app.vault.modify(activeFile, `${head}${nextBody}`);
    notice("Image hidden.");
    return;
  }

  const source = resolveImageSource(frontmatter);
  if (!source) {
    return fail("No image source found in frontmatter at image.source.");
  }

  const resolvedSource = resolveSourceForNote(app, activeFile.path, source);
  const nextBody = insertThumbnailBlock(body, resolvedSource);
  await app.vault.modify(activeFile, `${head}${nextBody}`);
  notice("Image shown.");
};

function normalizeFrontmatter(frontmatter) {
  if (!frontmatter || typeof frontmatter !== "object") return {};
  const out = {};
  for (const [key, value] of Object.entries(frontmatter)) {
    if (key === "position") continue;
    out[key] = value;
  }
  return out;
}

function resolveImageSource(frontmatter) {
  const image = frontmatter.image;
  if (image && typeof image === "object") {
    const source = String(image.source || "").trim();
    if (source) return source;
  }

  if (typeof image === "string") {
    const source = image.trim();
    if (source) return source;
  }

  return "";
}

function resolveSourceForNote(app, notePath, source) {
  const path = require("path");
  let value = normalizeSource(source);
  if (!value) return "";

  if (isWebUrl(value)) return value;

  const vaultRelative = toVaultRelativePath(app, value);
  if (path.posix.isAbsolute(vaultRelative)) {
    return vaultRelative;
  }

  const normalizedNotePath = String(notePath || "").replace(/\\/g, "/");
  const noteDir = path.posix.dirname(normalizedNotePath);
  const relative = path.posix.relative(noteDir, vaultRelative);
  return relative || path.posix.basename(vaultRelative);
}

function normalizeSource(source) {
  let value = String(source || "").trim();
  if (!value) return "";

  const wikilinkMatch = value.match(/^!?\[\[([\s\S]+?)\]\]$/);
  if (wikilinkMatch) value = wikilinkMatch[1].trim();

  const markdownMatch = value.match(/^!?\[[^\]]*]\(([\s\S]+)\)$/);
  if (markdownMatch) value = markdownMatch[1].trim();

  if (value.startsWith("<") && value.endsWith(">")) {
    value = value.slice(1, -1).trim();
  }

  if (!isWebUrl(value)) {
    if (value.includes("|")) {
      value = value.split("|")[0].trim();
    }
    value = value.replace(/\\/g, "/").replace(/^\.\/+/, "");
  }

  return value.trim();
}

function toVaultRelativePath(app, sourcePath) {
  const path = require("path");
  const normalized = String(sourcePath || "").replace(/\\/g, "/");
  if (!normalized) return "";
  if (path.posix.isAbsolute(normalized)) {
    const basePath = getVaultBasePath(app).replace(/\\/g, "/");
    const candidate = normalized;
    if (candidate === basePath) return "";
    if (candidate.startsWith(`${basePath}/`)) {
      return candidate.slice(basePath.length + 1);
    }
    return candidate;
  }
  return normalized.replace(/^\/+/, "");
}

function getVaultBasePath(app) {
  const adapter = app?.vault?.adapter;
  const basePath =
    (adapter && typeof adapter.getBasePath === "function" && adapter.getBasePath()) ||
    (adapter && adapter.basePath) ||
    "";
  return String(basePath || "");
}

function isWebUrl(value) {
  return /^https?:\/\//i.test(String(value || "").trim());
}

function splitNote(raw) {
  const text = String(raw || "").replace(/\r\n?/g, "\n");
  if (!text.startsWith("---\n")) return { head: "", body: text };

  const end = text.indexOf("\n---\n", 4);
  if (end === -1) return { head: "", body: text };

  return {
    head: text.slice(0, end + 5),
    body: text.slice(end + 5),
  };
}

function isContentPath(filePath) {
  const normalized = String(filePath || "").replace(/\\/g, "/");
  return (
    normalized.startsWith("content/") ||
    normalized.startsWith("contents/")
  );
}

function hasLeadingImageLink(body) {
  const text = String(body || "");
  return getLeadingLinkPattern().test(text);
}

function removeLeadingImageLink(body) {
  const text = String(body || "");
  return text.replace(getLeadingLinkPattern(), "");
}

function insertThumbnailBlock(body, source) {
  const text = String(body || "");
  const cleaned = text.replace(/^\n+/, "");
  const link = buildThumbnailLink(source);
  return cleaned ? `${link}\n\n${cleaned}` : `${link}\n`;
}

function buildThumbnailLink(source) {
  const value = String(source || "").trim();
  const wrapped = /\s/.test(value) ? `<${value}>` : value;
  return `![thumbnail](${wrapped}|${THUMB_WIDTH})`;
}

function getLeadingLinkPattern() {
  // Remove the first body element when it is an image/link line inserted for preview.
  return /^\n*(?:!\[[^\]]*]\([^\n]+\)|!\[\[[^\]\n]+\]\]|\[[^\]]+]\([^\n]+\))\s*\n{0,2}/;
}
