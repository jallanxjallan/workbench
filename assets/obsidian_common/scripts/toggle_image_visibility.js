function notice(message, timeout = 9000) {
  if (typeof Notice === "function") new Notice(message, timeout);
  console.log(message);
}

function fail(message) {
  const text = `Update Images failed: ${message}`;
  if (typeof Notice === "function") new Notice(text, 10000);
  console.error(text);
}

const THUMB_WIDTH = 240;
const IMAGE_EXTENSIONS = new Set([
  ".apng",
  ".avif",
  ".bmp",
  ".gif",
  ".heic",
  ".heif",
  ".ico",
  ".jfif",
  ".jpeg",
  ".jpg",
  ".png",
  ".svg",
  ".tif",
  ".tiff",
  ".webp",
]);

module.exports = async function updateImages(params = {}) {
  const app = params.app || globalThis.app;
  if (!app || !app.vault || !app.metadataCache) {
    return fail("Obsidian app context not available.");
  }

  const files = app.vault.getMarkdownFiles().filter((file) => isContentPath(file.path));
  if (files.length === 0) {
    notice("Update Images: no markdown files found in content folders.");
    return;
  }

  let classImageCount = 0;
  let changedCount = 0;
  let errorCount = 0;

  for (const file of files) {
    try {
      const cache = app.metadataCache.getFileCache(file) || {};
      const cacheFrontmatter = normalizeFrontmatter(cache.frontmatter);
      const noteClass = String(cacheFrontmatter.class || cacheFrontmatter.type || "")
        .trim()
        .toLowerCase();

      if (noteClass !== "image") continue;
      classImageCount += 1;

      const raw = await app.vault.read(file);
      const { head, body } = splitNote(raw);

      const parsedFrontmatter = parseFrontmatterFromHead(head, cacheFrontmatter);
      const rewritten = rewriteEmbedsAsThumbnails(body);

      const sourceCandidate =
        rewritten.primarySource ||
        readSourceFromFrontmatter(parsedFrontmatter) ||
        readSourceFromFrontmatter(cacheFrontmatter);
      const imageLink = normalizeImageLinkForFrontmatter(app, file.path, sourceCandidate);

      const nextFrontmatter = syncImagesFrontmatter(parsedFrontmatter, imageLink);
      const frontmatterChanged = !isDeepEqual(parsedFrontmatter, nextFrontmatter);
      const bodyChanged = rewritten.body !== body;

      if (!frontmatterChanged && !bodyChanged) continue;

      const nextHead = frontmatterChanged ? composeFrontmatterHead(nextFrontmatter) : head;
      const nextBody = bodyChanged ? rewritten.body : body;
      await app.vault.modify(file, `${nextHead}${nextBody}`);
      changedCount += 1;
    } catch (error) {
      errorCount += 1;
      console.error(`Update Images failed for ${file.path}:`, error);
    }
  }

  const summary = `Update Images: scanned ${classImageCount} class:image notes, updated ${changedCount}${
    errorCount ? `, errors ${errorCount}` : ""
  }.`;

  if (errorCount > 0) {
    if (typeof Notice === "function") new Notice(summary, 12000);
    console.warn(summary);
    return;
  }

  notice(summary);
};

function rewriteEmbedsAsThumbnails(body) {
  const text = String(body || "");
  const sources = [];

  const replaced = text.replace(
    /!\[[^\]\n]*\]\(([^)\n]+)\)|!\[\[([^\]\n]+)\]\]/g,
    (match, markdownSource, wikilinkSource) => {
      const source = normalizeSource(stripPreviewOptions(markdownSource || wikilinkSource || ""));
      if (!source || !looksLikeImageSource(source)) return match;
      sources.push(source);
      return buildThumbnailLink(source);
    },
  );

  return {
    body: replaced,
    sources,
    primarySource: sources[0] || "",
  };
}

function syncImagesFrontmatter(frontmatter, imageLink) {
  const next = cloneValue(frontmatter);
  const images = normalizeImagesObject(next.images);

  const legacyImage = next.image;
  if (isPlainObject(legacyImage)) {
    for (const [key, value] of Object.entries(legacyImage)) {
      if (key === "source") continue;
      if (images[key] === undefined) images[key] = cloneValue(value);
    }

    if (!images.image_link) {
      const legacySource = String(legacyImage.source || "").trim();
      if (legacySource) images.image_link = legacySource;
    }
  } else if (typeof legacyImage === "string" && !images.image_link) {
    const legacySource = legacyImage.trim();
    if (legacySource) images.image_link = legacySource;
  }

  if (imageLink) images.image_link = imageLink;
  if (!images.image_link) images.image_link = "";

  next.images = images;

  if (isPlainObject(legacyImage)) {
    const syncedLegacy = cloneValue(legacyImage);
    if (imageLink) syncedLegacy.source = imageLink;
    else if (!syncedLegacy.source) syncedLegacy.source = "";
    next.image = syncedLegacy;
  }

  return next;
}

function readSourceFromFrontmatter(frontmatter) {
  if (!frontmatter || typeof frontmatter !== "object") return "";

  const images = frontmatter.images;
  if (isPlainObject(images)) {
    const source = String(images.image_link || "").trim();
    if (source) return source;
  }

  const image = frontmatter.image;
  if (isPlainObject(image)) {
    const source = String(image.source || "").trim();
    if (source) return source;
  }

  if (typeof image === "string") {
    const source = image.trim();
    if (source) return source;
  }

  return "";
}

function normalizeImageLinkForFrontmatter(app, notePath, source) {
  const value = normalizeSource(source);
  if (!value) return "";
  if (isWebUrl(value)) return value;

  const absolute = resolveAbsoluteSourcePath(app, notePath, value);
  if (!absolute) return value;
  if (isWebUrl(absolute)) return absolute;

  const vaultRelative = toVaultRelativePath(app, absolute);
  return vaultRelative || value;
}

function normalizeFrontmatter(frontmatter) {
  if (!frontmatter || typeof frontmatter !== "object") return {};
  const out = {};
  for (const [key, value] of Object.entries(frontmatter)) {
    if (key === "position") continue;
    out[key] = value;
  }
  return out;
}

function normalizeImagesObject(imagesValue) {
  if (isPlainObject(imagesValue)) return cloneValue(imagesValue);

  if (Array.isArray(imagesValue)) {
    for (const item of imagesValue) {
      if (isPlainObject(item)) return cloneValue(item);
    }
  }

  return {};
}

function isPlainObject(value) {
  return Object.prototype.toString.call(value) === "[object Object]";
}

function cloneValue(value) {
  if (Array.isArray(value)) return value.map((item) => cloneValue(item));
  if (isPlainObject(value)) {
    const out = {};
    for (const [key, item] of Object.entries(value)) out[key] = cloneValue(item);
    return out;
  }
  return value;
}

function isDeepEqual(left, right) {
  return stableSerialize(left) === stableSerialize(right);
}

function stableSerialize(value) {
  if (value === undefined) return '"__undefined__"';
  if (value === null) return "null";

  if (Array.isArray(value)) {
    return `[${value.map((item) => stableSerialize(item)).join(",")}]`;
  }

  if (isPlainObject(value)) {
    const keys = Object.keys(value).sort();
    return `{${keys
      .map((key) => `${JSON.stringify(key)}:${stableSerialize(value[key])}`)
      .join(",")}}`;
  }

  return JSON.stringify(value);
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

function parseFrontmatterFromHead(head, fallbackFrontmatter = {}) {
  const text = String(head || "");
  if (!text.startsWith("---\n") || !text.endsWith("\n---\n")) {
    return normalizeFrontmatter(fallbackFrontmatter);
  }

  const yamlRaw = text.slice(4, -5);
  const parseYaml = globalThis?.obsidian?.parseYaml;
  if (typeof parseYaml === "function") {
    try {
      const parsed = parseYaml(yamlRaw);
      if (parsed && typeof parsed === "object") {
        return normalizeFrontmatter(parsed);
      }
    } catch (_) {
      // Fall back to metadata cache frontmatter.
    }
  }

  return normalizeFrontmatter(fallbackFrontmatter);
}

function composeFrontmatterHead(frontmatter) {
  const fm = normalizeFrontmatter(frontmatter);
  const stringifyYaml = globalThis?.obsidian?.stringifyYaml;

  let yaml = "";
  if (typeof stringifyYaml === "function") {
    yaml = String(stringifyYaml(fm || {})).trimEnd();
  } else {
    yaml = toYamlObject(fm || {}, 0).join("\n");
  }

  return `---\n${yaml}\n---\n`;
}

function toYamlObject(obj, indent) {
  const pad = " ".repeat(indent);
  const lines = [];

  for (const [key, value] of Object.entries(obj || {})) {
    if (isPlainObject(value)) {
      const keys = Object.keys(value);
      if (keys.length === 0) {
        lines.push(`${pad}${key}: {}`);
      } else {
        lines.push(`${pad}${key}:`);
        lines.push(...toYamlObject(value, indent + 2));
      }
      continue;
    }

    if (Array.isArray(value)) {
      if (value.length === 0) {
        lines.push(`${pad}${key}: []`);
      } else {
        lines.push(`${pad}${key}:`);
        lines.push(...toYamlArray(value, indent + 2));
      }
      continue;
    }

    lines.push(`${pad}${key}: ${toYamlScalar(value)}`);
  }

  return lines;
}

function toYamlArray(arr, indent) {
  const pad = " ".repeat(indent);
  const lines = [];

  for (const item of arr) {
    if (isPlainObject(item)) {
      const keys = Object.keys(item);
      if (keys.length === 0) {
        lines.push(`${pad}- {}`);
      } else {
        lines.push(`${pad}-`);
        lines.push(...toYamlObject(item, indent + 2));
      }
      continue;
    }

    if (Array.isArray(item)) {
      lines.push(`${pad}- ${toYamlScalar(JSON.stringify(item))}`);
      continue;
    }

    lines.push(`${pad}- ${toYamlScalar(item)}`);
  }

  return lines;
}

function toYamlScalar(value) {
  if (value === null) return "null";
  if (value === undefined) return '""';
  if (typeof value === "boolean" || typeof value === "number") return String(value);

  const text = String(value);
  if (!text.trim()) return '""';
  if (/[:#\-\[\]\{\}\n]/.test(text)) return JSON.stringify(text);
  return text;
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
    value.startsWith("../") || value.startsWith("./") ? [fromNote, fromVault] : [fromVault, fromNote];

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return candidate;
  }

  return candidates[0];
}

function toVaultRelativePath(app, sourcePath) {
  const path = require("path");
  const normalized = String(sourcePath || "").replace(/\\/g, "/");
  if (!normalized) return "";

  if (path.posix.isAbsolute(normalized)) {
    const basePath = getVaultBasePath(app).replace(/\\/g, "/");
    if (normalized === basePath) return "";
    if (normalized.startsWith(`${basePath}/`)) {
      return normalized.slice(basePath.length + 1);
    }
    return normalized;
  }

  return normalized.replace(/^\/+/, "");
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

function buildThumbnailLink(source) {
  const value = String(source || "").trim();
  const wrapped = /\s/.test(value) ? `<${value}>` : value;
  return `![thumbnail|${THUMB_WIDTH}](${wrapped})`;
}

function looksLikeImageSource(source) {
  const value = String(source || "").trim();
  if (!value) return false;

  if (isWebUrl(value)) {
    try {
      const { pathname } = new URL(value);
      return IMAGE_EXTENSIONS.has(getExtension(pathname));
    } catch (_) {
      return false;
    }
  }

  return IMAGE_EXTENSIONS.has(getExtension(value));
}

function getExtension(pathValue) {
  const value = String(pathValue || "");
  const queryIndex = value.indexOf("?");
  const clean = queryIndex >= 0 ? value.slice(0, queryIndex) : value;
  const dot = clean.lastIndexOf(".");
  if (dot < 0) return "";
  return clean.slice(dot).toLowerCase();
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

function isContentPath(filePath) {
  const normalized = String(filePath || "").replace(/\\/g, "/");
  return normalized.startsWith("content/") || normalized.startsWith("contents/");
}
