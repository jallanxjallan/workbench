const path = require("path");

const RUNTIME_BLOCK_PATTERN = /^```create-note-runtime\s*\n([\s\S]*?)\n```[ \t]*$/gm;
const PLACEHOLDER_SLUGS = new Set([
  "",
  "__slug__",
  "<slug>",
  "slug",
  "todo",
  "tbd",
  "null",
  "undefined",
]);
const ACTIVE_NOTE_TYPES = new Set(["content", "instruction", "topic"]);

async function executeEmbeddedTemplateMacro({ app: candidateApp, file, params = {} } = {}) {
  const app = resolveApp(candidateApp);
  if (!app || !file?.path) {
    throw new Error("Obsidian app context and created file are required.");
  }

  const text = await app.vault.cachedRead(file);
  const runtimeBlock = extractEmbeddedRuntimeBlock(text);
  const helpers = createTemplateHelpers(app);
  const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
  const runnerSource = [
    "const { app, file, helpers, notice, params, require } = context;",
    "return (async () => {",
    runtimeBlock.code,
    "})();",
  ].join("\n");
  const runner = new AsyncFunction("context", runnerSource);

  const result = await runner({
    app,
    file,
    helpers,
    notice,
    params,
    require,
  });

  if (result === false || result?.ok === false) {
    throw new Error(result?.message || "Embedded template macro returned failure.");
  }

  return result;
}

async function validateCreatedNote({ app: candidateApp, file } = {}) {
  const app = resolveApp(candidateApp);
  if (!app || !file?.path) {
    throw new Error("Obsidian app context and created file are required.");
  }

  const text = await app.vault.cachedRead(file);
  const frontmatter = locateFrontmatter(text);
  if (!frontmatter) {
    throw new Error("Created note is missing frontmatter.");
  }

  const slug = stripQuotes(readFrontmatterValue(text, "slug"));
  if (!slug) {
    throw new Error("Created note is missing slug.");
  }
  if (isPlaceholderSlug(slug)) {
    throw new Error("Created note slug is still a placeholder.");
  }
  if (countEmbeddedRuntimeBlocks(text) > 0) {
    throw new Error("Created note still contains an unresolved embedded runtime block.");
  }

  const schemaHelper = loadSlugSchemaHelper(app);
  const schema = schemaHelper.load_slug_schema(app);
  if (!schemaHelper.validate_slug(slug, schema)) {
    throw new Error(`Created note slug failed schema validation: ${slug}`);
  }

  const duplicates = await findDuplicateSlugPaths(app, slug, file.path);
  if (duplicates.length > 0) {
    throw new Error(`Created note slug duplicates an existing note: ${duplicates[0]}`);
  }

  return {
    path: file.path,
    slug,
  };
}

async function deleteFile({ app: candidateApp, file } = {}) {
  const app = resolveApp(candidateApp);
  if (!app || !file?.path) {
    throw new Error("Obsidian app context and file are required for deletion.");
  }

  const existing = app.vault.getAbstractFileByPath?.(file.path);
  if (!existing) {
    return;
  }

  if (typeof app.vault.delete === "function") {
    await app.vault.delete(existing);
    return;
  }

  if (typeof app.fileManager?.trashFile === "function") {
    await app.fileManager.trashFile(existing);
    return;
  }

  throw new Error(`Could not delete file: ${file.path}`);
}

function createTemplateHelpers(app) {
  const slugHelper = loadSlugHelper(app);
  const schemaHelper = loadSlugSchemaHelper(app);
  const schema = schemaHelper.load_slug_schema(app);

  return {
    notice,
    async initializeCreatedNote({
      file,
      noteType,
      parts = {},
      frontmatter = {},
      removeRuntimeBlock = true,
    } = {}) {
      if (!file?.path) {
        throw new Error("Template helper requires a created file.");
      }

      const normalizedNoteType = normalizeNoteType(noteType);
      if (!normalizedNoteType) {
        throw new Error("Template helper requires a valid note type.");
      }

      if (Object.keys(frontmatter).length > 0) {
        await setFrontmatterFields({ app, file, frontmatter });
      }

      const currentText = await app.vault.cachedRead(file);
      let updatedText = currentText;
      let slug = stripQuotes(readFrontmatterValue(currentText, "slug"));

      if (!slug || isPlaceholderSlug(slug)) {
        slug = buildSlugFromTemplate({
          app,
          file,
          parts,
          schema,
          schemaHelper,
          slugHelper,
          sourceText: currentText,
        });
        updatedText = slugHelper.replace_frontmatter_field(updatedText, "slug", slug);
      }

      if (removeRuntimeBlock) {
        updatedText = stripEmbeddedRuntimeBlock(updatedText);
      }

      if (updatedText !== currentText) {
        await app.vault.modify(file, updatedText);
      }

      const message = formatCreatedMessage(normalizedNoteType);
      notice(message, 8000);
      return message;
    },
    async removeRuntimeBlock({ file } = {}) {
      if (!file?.path) {
        throw new Error("Template helper requires a created file.");
      }

      const current = await app.vault.cachedRead(file);
      const updated = stripEmbeddedRuntimeBlock(current);
      if (updated !== current) {
        await app.vault.modify(file, updated);
      }
      return updated;
    },
    async setFrontmatterFields({ file, frontmatter } = {}) {
      return setFrontmatterFields({ app, file, frontmatter });
    },
    async validateCreatedNote({ file } = {}) {
      return validateCreatedNote({ app, file });
    },
  };
}

function normalizeNoteType(value) {
  const normalized = normalizeString(value).toLowerCase();
  if (!ACTIVE_NOTE_TYPES.has(normalized)) {
    return "";
  }
  return normalized;
}

function formatCreatedMessage(noteType) {
  return `Created ${noteType} note.`;
}

function buildSlugFromTemplate({
  app,
  file,
  parts = {},
  schema,
  schemaHelper,
  slugHelper,
  sourceText,
}) {
  const text = String(sourceText || "");
  const separator = schema?.slug?.separator || ".";
  const fields = Array.isArray(schema?.slug?.fields) ? schema.slug.fields : [];
  if (fields.length === 0) {
    throw new Error("Slug schema has no fields.");
  }

  const resolved = {};
  for (const field of fields) {
    const fieldName = normalizeString(field?.name);
    if (!fieldName || fieldName === "identity" || fieldName === "seq") {
      continue;
    }

    const rawValue = resolveSlugPart({
      app,
      fieldName,
      file,
      parts,
      slugHelper,
      sourceText: text,
    });

    if (!rawValue) {
      if (field?.required) {
        throw new Error(`Template macro could not resolve required slug part: ${fieldName}`);
      }
      continue;
    }

    const normalizedValue = normalizeSlugPart(field, rawValue, schemaHelper);
    validateSlugPart(field, normalizedValue);
    resolved[fieldName] = normalizedValue;
  }

  const baseFields = fields
    .map((field) => normalizeString(field?.name))
    .filter((fieldName) => fieldName && fieldName !== "identity" && fieldName !== "seq");
  const missingBaseFields = baseFields.filter((fieldName) => !resolved[fieldName]);
  if (missingBaseFields.length > 0) {
    throw new Error(`Template macro is missing slug parts: ${missingBaseFields.join(", ")}`);
  }

  const base = baseFields.map((fieldName) => resolved[fieldName]).join(separator);
  resolved.identity = normalizeIdentity(schemaHelper.hash_alpha(base, 8).slice(0, 8));

  const seqField = fields.find((field) => normalizeString(field?.name) === "seq");
  if (seqField) {
    const rawSeq = resolveSlugPart({
      app,
      fieldName: "seq",
      file,
      parts,
      slugHelper,
      sourceText: text,
    });
    if (normalizeString(rawSeq)) {
      resolved.seq = String(rawSeq).trim().padStart(3, "0");
      validateSlugPart(seqField, resolved.seq);
    }
  }

  const slug = fields
    .map((field) => normalizeString(field?.name))
    .filter((fieldName) => fieldName && normalizeString(resolved[fieldName]))
    .map((fieldName) => resolved[fieldName])
    .join(separator);

  if (!schemaHelper.validate_slug(slug, schema)) {
    throw new Error(`Generated slug failed schema validation: ${slug}`);
  }

  return slug;
}

function resolveSlugPart({ app, fieldName, file, parts, slugHelper, sourceText }) {
  if (parts[fieldName] !== undefined && parts[fieldName] !== null) {
    return parts[fieldName];
  }

  if (fieldName === "type") {
    return slugHelper.read_slug_prefix(sourceText);
  }
  if (fieldName === "project") {
    return slugHelper.resolve_project_mnemonic(app);
  }
  if (fieldName === "hint") {
    return slugHelper.normalize_hint(path.basename(file.path, path.extname(file.path)));
  }

  return readFrontmatterValue(sourceText, fieldName);
}

function normalizeSlugPart(field, value, schemaHelper) {
  const fieldName = normalizeString(field?.name);
  if (fieldName === "seq") {
    return String(value || "").trim().padStart(3, "0");
  }
  if (fieldName === "identity") {
    return normalizeIdentity(value);
  }
  return schemaHelper.normalize_component(String(value || ""));
}

function normalizeIdentity(value) {
  return normalizeString(value).toLowerCase().replace(/[^a-z]/g, "");
}

function validateSlugPart(field, value) {
  const pattern = normalizeString(field?.pattern);
  if (!pattern) {
    throw new Error(`Slug schema field is missing a pattern: ${field?.name || "unknown"}`);
  }

  const matcher = new RegExp(`^(?:${pattern})$`);
  if (!matcher.test(String(value || ""))) {
    throw new Error(`Slug part failed validation for ${field.name}: ${value}`);
  }
}

async function setFrontmatterFields({ app, file, frontmatter = {} } = {}) {
  if (!file?.path || Object.keys(frontmatter).length === 0) {
    return;
  }

  if (!app.fileManager || typeof app.fileManager.processFrontMatter !== "function") {
    throw new Error("Obsidian fileManager.processFrontMatter is unavailable.");
  }

  await app.fileManager.processFrontMatter(file, (current) => {
    for (const [key, value] of Object.entries(frontmatter)) {
      current[key] = cloneJsonLike(value);
    }
  });
}

async function findDuplicateSlugPaths(app, slug, excludePath = "") {
  const duplicates = [];
  const files = app.vault.getMarkdownFiles ? app.vault.getMarkdownFiles() : [];

  for (const candidate of files) {
    if (!candidate?.path || candidate.path === excludePath) {
      continue;
    }

    const cachedSlug = stripQuotes(app.metadataCache?.getFileCache(candidate)?.frontmatter?.slug);
    let candidateSlug = cachedSlug;
    if (!candidateSlug) {
      try {
        candidateSlug = stripQuotes(readFrontmatterValue(await app.vault.cachedRead(candidate), "slug"));
      } catch (_error) {
        candidateSlug = "";
      }
    }

    if (candidateSlug === slug) {
      duplicates.push(candidate.path);
    }
  }

  return duplicates.sort();
}

function countEmbeddedRuntimeBlocks(sourceText) {
  return listEmbeddedRuntimeBlocks(sourceText).length;
}

function extractEmbeddedRuntimeBlock(sourceText) {
  const matches = listEmbeddedRuntimeBlocks(sourceText);
  if (matches.length === 0) {
    throw new Error("Template is missing an embedded create-note runtime block.");
  }
  if (matches.length > 1) {
    throw new Error("Template contains multiple embedded create-note runtime blocks.");
  }
  return matches[0];
}

function listEmbeddedRuntimeBlocks(sourceText) {
  const normalized = String(sourceText || "");
  const pattern = new RegExp(RUNTIME_BLOCK_PATTERN.source, RUNTIME_BLOCK_PATTERN.flags);
  const matches = [];
  for (const match of normalized.matchAll(pattern)) {
    matches.push({
      code: match[1],
      raw: match[0],
    });
  }
  return matches;
}

function stripEmbeddedRuntimeBlock(sourceText) {
  const runtimeBlock = extractEmbeddedRuntimeBlock(sourceText);
  const normalized = String(sourceText || "");
  return normalized.replace(runtimeBlock.raw, "").replace(/\n{3,}/g, "\n\n").trimEnd() + "\n";
}

function isPlaceholderSlug(value) {
  const normalized = stripQuotes(value).toLowerCase();
  return (
    PLACEHOLDER_SLUGS.has(normalized) ||
    !normalized.includes(".") ||
    normalized.endsWith(".") ||
    /[<>{}]/.test(normalized)
  );
}

function resolveApp(candidateApp) {
  if (candidateApp?.vault?.adapter) {
    return candidateApp;
  }

  if (typeof window !== "undefined" && window?.app?.vault?.adapter) {
    return window.app;
  }

  return candidateApp;
}

function getVaultBasePath(app) {
  const adapter = app?.vault?.adapter;
  const basePath =
    (adapter && typeof adapter.getBasePath === "function" && adapter.getBasePath()) ||
    adapter?.basePath ||
    "";

  if (!basePath) {
    throw new Error("Vault base path is unavailable.");
  }

  return String(basePath);
}

function loadSlugHelper(app) {
  return require(path.join(getVaultBasePath(app), "_control", "scripts", "slug.js"));
}

function loadSlugSchemaHelper(app) {
  return require(path.join(getVaultBasePath(app), "_control", "scripts", "slug_schema.js"));
}

function notice(message, timeout = 8000) {
  if (typeof Notice === "function") {
    new Notice(message, timeout);
  }
  console.log(message);
}

function locateFrontmatter(sourceText) {
  const normalized = String(sourceText || "");
  if (!normalized.startsWith("---\n")) {
    return null;
  }

  const end = normalized.indexOf("\n---\n", 4);
  if (end === -1) {
    return null;
  }

  return {
    block: normalized.slice(4, end),
    body: normalized.slice(end + 5),
  };
}

function readFrontmatterValue(sourceText, field) {
  const frontmatter = locateFrontmatter(sourceText);
  if (!frontmatter) {
    return "";
  }

  const matcher = new RegExp(`^${escapePattern(field)}\\s*:(.*)$`);
  for (const line of frontmatter.block.split("\n")) {
    const match = line.match(matcher);
    if (match) {
      return stripQuotes(match[1]);
    }
  }

  return "";
}

function escapePattern(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function normalizeString(value) {
  return String(value || "").trim();
}

function stripQuotes(value) {
  return normalizeString(value).replace(/^['"]|['"]$/g, "");
}

function cloneJsonLike(value) {
  if (typeof structuredClone === "function") {
    return structuredClone(value);
  }
  return JSON.parse(JSON.stringify(value));
}

module.exports = {
  countEmbeddedRuntimeBlocks,
  createTemplateHelpers,
  deleteFile,
  executeEmbeddedTemplateMacro,
  extractEmbeddedRuntimeBlock,
  findDuplicateSlugPaths,
  stripEmbeddedRuntimeBlock,
  validateCreatedNote,
  _test: {
    buildSlugFromTemplate,
    isPlaceholderSlug,
    readFrontmatterValue,
    resolveSlugPart,
    stripEmbeddedRuntimeBlock,
    validateSlugPart,
  },
};
