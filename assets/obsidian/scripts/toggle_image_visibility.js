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
  const noteClass = String(frontmatter.class || frontmatter.type || "").trim().toLowerCase();
  if (noteClass !== "image") {
    return fail("Active file is not class: image.");
  }

  const raw = await app.vault.read(activeFile);
  const { head, body } = splitNote(raw);

  if (hasLeadingImageLink(body)) {
    const sourceFromBody = extractLeadingImageSource(body);
    if (!sourceFromBody) {
      return fail("Could not resolve image source from leading body image link.");
    }

    const sourceForMetadata = resolveSourceForMetadata(
      app,
      activeFile.path,
      sourceFromBody,
    );
    const nextBody = removeLeadingImageLink(body);
    const nextHead = setImageSourceInFrontmatter(head, sourceForMetadata);
    await app.vault.modify(activeFile, `${nextHead}${nextBody}`);
    notice("Image hidden.");
    return;
  }

  const source = resolveImageSource(frontmatter);
  if (!source) {
    return fail("No image source found in frontmatter at image.source.");
  }

  const resolvedSource = resolveSourceForNote(app, activeFile.path, source);
  const nextBody = insertThumbnailBlock(body, resolvedSource);
  const nextHead = setImageSourceInFrontmatter(head, "");
  await app.vault.modify(activeFile, `${nextHead}${nextBody}`);
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
  const absoluteOrWeb = resolveAbsoluteSourcePath(app, notePath, source);
  if (!absoluteOrWeb) return "";
  if (isWebUrl(absoluteOrWeb)) return absoluteOrWeb;
  return toFileUrl(absoluteOrWeb);
}

function resolveSourceForMetadata(app, notePath, source) {
  return resolveAbsoluteSourcePath(app, notePath, source);
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
    const filePath = fileUrlToPath(value);
    if (filePath) value = filePath;

    if (value.includes("|")) {
      value = value.split("|")[0].trim();
    }
    value = value.replace(/\\/g, "/").replace(/^\.\/+/, "");
  }

  return value.trim();
}

function resolveAbsoluteSourcePath(app, notePath, source) {
  const fs = require("fs");
  const path = require("path");
  const value = normalizeSource(source);
  if (!value) return "";
  if (isWebUrl(value)) return value;

  if (path.posix.isAbsolute(value)) {
    return path.posix.normalize(value);
  }

  const basePath = getVaultBasePath(app).replace(/\\/g, "/");
  if (!basePath) return value;

  const normalizedNotePath = String(notePath || "").replace(/\\/g, "/");
  const noteAbsDir = path.posix.dirname(path.posix.join(basePath, normalizedNotePath));
  const fromVault = path.posix.normalize(path.posix.join(basePath, value));
  const fromNote = path.posix.normalize(path.posix.join(noteAbsDir, value));

  const candidates =
    value.startsWith("../") || value.startsWith("./")
      ? [fromNote, fromVault]
      : [fromVault, fromNote];

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return candidate;
  }

  return candidates[0];
}

function toFileUrl(absolutePath) {
  try {
    const { pathToFileURL } = require("url");
    return pathToFileURL(String(absolutePath || "")).toString();
  } catch (_) {
    const value = String(absolutePath || "").replace(/\\/g, "/");
    return value ? `file://${encodeURI(value)}` : "";
  }
}

function fileUrlToPath(value) {
  const text = String(value || "").trim();
  if (!/^file:\/\//i.test(text)) return "";
  try {
    const url = new URL(text);
    if (url.protocol !== "file:") return "";
    return decodeURIComponent(url.pathname || "");
  } catch (_) {
    return "";
  }
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

function extractLeadingImageSource(body) {
  const text = String(body || "");
  const markdown = text.match(/^\n*!\[[^\]]*]\(([^)\n]+)\)/);
  if (markdown) {
    return normalizeSource(stripPreviewOptions(markdown[1]));
  }

  const wikilink = text.match(/^\n*!\[\[([^\]\n]+)\]\]/);
  if (wikilink) {
    return normalizeSource(stripPreviewOptions(wikilink[1]));
  }

  return "";
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
  return `![thumbnail|${THUMB_WIDTH}](${wrapped})`;
}

function setImageSourceInFrontmatter(head, source) {
  const text = String(head || "");
  if (!text.startsWith("---\n")) return text;

  const lines = text.split("\n");
  const imageHeader = findImageBlockHeader(lines);
  if (imageHeader < 0) return text;

  const sourceLine = findImageSourceLine(lines, imageHeader);
  const renderedValue = renderYamlScalar(source);

  if (sourceLine >= 0) {
    const prefixMatch = lines[sourceLine].match(/^(\s*source:\s*)/);
    const prefix = prefixMatch ? prefixMatch[1] : "";
    lines[sourceLine] = `${prefix}${renderedValue}`;
  } else {
    const imageIndent = leadingSpaceCount(lines[imageHeader]);
    const insertAt = imageHeader + 1;
    const indent = " ".repeat(imageIndent + 2);
    lines.splice(insertAt, 0, `${indent}source: ${renderedValue}`);
  }

  return lines.join("\n");
}

function findImageBlockHeader(lines) {
  for (let i = 1; i < lines.length; i += 1) {
    if (/^\s*image:\s*$/.test(lines[i])) return i;
  }
  return -1;
}

function findImageSourceLine(lines, imageHeader) {
  const imageIndent = leadingSpaceCount(lines[imageHeader]);
  for (let i = imageHeader + 1; i < lines.length; i += 1) {
    const line = String(lines[i] || "");
    if (/^---\s*$/.test(line)) break;
    if (!line.trim()) continue;

    const indent = leadingSpaceCount(line);
    if (indent <= imageIndent && /^\s*[\w-]+\s*:/.test(line)) break;
    if (/^\s*source\s*:/.test(line)) return i;
  }
  return -1;
}

function leadingSpaceCount(line) {
  const match = String(line || "").match(/^(\s*)/);
  return match ? match[1].length : 0;
}

function renderYamlScalar(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  if (isWebUrl(text)) return text;
  if (/^[A-Za-z0-9._\-\/]+$/.test(text)) return text;
  return JSON.stringify(text);
}

function stripPreviewOptions(value) {
  const text = String(value || "").trim();
  if (!text) return "";

  if (text.startsWith("<")) {
    const close = text.indexOf(">");
    if (close >= 0) return text.slice(0, close + 1).trim();
  }

  const pipe = text.indexOf("|");
  if (pipe >= 0) return text.slice(0, pipe).trim();
  return text;
}

function getLeadingLinkPattern() {
  // Remove the first body element when it is an image/link line inserted for preview.
  return /^\n*(?:!\[[^\]]*]\([^\n]+\)|!\[\[[^\]\n]+\]\])\s*\n{0,2}/;
}
