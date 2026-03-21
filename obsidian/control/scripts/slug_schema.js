const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const ALPHABET = "abcdefghijklmnopqrstuvwxyz";
const SCHEMA_PATH = path.join("_control", "slug_schema.json");

function resolveApp(candidate) {
  if (candidate?.vault?.adapter) {
    return candidate;
  }
  if (typeof window !== "undefined" && window?.app?.vault?.adapter) {
    return window.app;
  }
  return null;
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

function loadSlugSchema(appOrPath) {
  const explicitPath = typeof appOrPath === "string" ? appOrPath : null;
  const app = explicitPath ? null : resolveApp(appOrPath);
  const schemaPath = explicitPath || path.join(getVaultBasePath(app), SCHEMA_PATH);

  if (!fs.existsSync(schemaPath)) {
    throw new Error(`Slug schema is missing: ${schemaPath}`);
  }

  try {
    return JSON.parse(fs.readFileSync(schemaPath, "utf8"));
  } catch (error) {
    const message = error?.message || String(error);
    throw new Error(`Could not parse slug schema: ${message}`);
  }
}

function normalizeRegexPattern(pattern) {
  return String(pattern || "").replace(/\(\?P<([a-zA-Z_][a-zA-Z0-9_]*)>/g, "(?<$1>");
}

function validateSlug(slug, schema) {
  const pattern = schema?.slug?.regex?.normalized;
  if (!pattern) {
    throw new Error("Slug schema missing slug.regex.normalized.");
  }
  return new RegExp(normalizeRegexPattern(pattern)).test(String(slug || ""));
}

function normalizeComponent(value) {
  const normalized = String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/-{2,}/g, "-");

  if (!normalized) {
    throw new Error("Slug component normalized to an empty value.");
  }

  return normalized;
}

function hashAlpha(value, length = 8) {
  let seed = Buffer.from(String(value || ""), "utf8");
  let output = "";

  while (output.length < length) {
    seed = crypto.createHash("sha256").update(seed).digest();
    for (const byte of seed) {
      output += ALPHABET[byte % ALPHABET.length];
      if (output.length >= length) {
        break;
      }
    }
  }

  return output;
}

function buildSlug(parts, schema) {
  const separator = schema?.slug?.separator || ".";
  const baseParts = [
    normalizeComponent(parts?.type),
    normalizeComponent(parts?.context),
    normalizeComponent(parts?.hint),
  ];

  const base = baseParts.join(separator);
  const identity = hashAlpha(base, 8);
  const slugParts = [...baseParts, identity];

  if (parts?.seq !== undefined && parts?.seq !== null && String(parts.seq).trim() !== "") {
    slugParts.push(String(parts.seq).padStart(3, "0"));
  }

  const slug = slugParts.join(separator);
  if (!validateSlug(slug, schema)) {
    throw new Error(`Generated slug does not satisfy schema: ${slug}`);
  }

  return slug;
}

module.exports = {
  build_slug: buildSlug,
  hash_alpha: hashAlpha,
  load_slug_schema: loadSlugSchema,
  normalize_component: normalizeComponent,
  validate_slug: validateSlug,
};
