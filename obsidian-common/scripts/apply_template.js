// apply_template.js — Apply a selected template to the active note.
// Rules:
// - Template sources: _common/template, _common/templates, and vault-root templates/.
// - Fails only if active file already has a slug property.
// - Fails if active file is not markdown or contains Dataview code blocks.
// - Sets slug (kebab-case parent + filename) and project.

module.exports = async (params = {}) => {
  const app = params.app || globalThis.app;
  const qa = params.quickAddApi || params.quickAdd;

  if (!app || !app.vault || !app.metadataCache) {
    return fail("Obsidian app context not available.");
  }
  if (!qa || typeof qa.suggester !== "function") {
    return fail("QuickAdd API not available.");
  }

  const activeFile = app.workspace?.getActiveFile?.();
  if (!activeFile) return fail("No active file.");
  if (activeFile.extension !== "md") {
    return fail("Active file must be a markdown note.");
  }

  const currentText = await app.vault.read(activeFile);
  if (containsDataview(currentText)) {
    return fail("Active note looks like a Dataview query note; aborting.");
  }

  const currentFm = normalizeFrontmatter(app.metadataCache.getFileCache(activeFile)?.frontmatter);
  if (Object.prototype.hasOwnProperty.call(currentFm, "slug")) {
    return fail("Active note already has a slug property; aborting.");
  }

  const templates = collectTemplates(app);
  if (templates.length === 0) {
    return fail("No templates found in _common/template, _common/templates, or templates/.");
  }

  const labels = templates.map((t) => t.label);
  const picked = await qa.suggester(labels, templates, "Pick template");
  if (!picked) return notice("Cancelled.");

  const templateText = await app.vault.read(picked.file);
  const parsedTemplate = splitFrontmatter(templateText);
  let templateFm = normalizeFrontmatter(app.metadataCache.getFileCache(picked.file)?.frontmatter);
  if (Object.keys(templateFm).length === 0) {
    templateFm = normalizeFrontmatter(parsedTemplate.frontmatter);
  }
  const templateBody = parsedTemplate.body;

  const slug = buildSlug(activeFile.path);
  const project = await resolveProjectName(app);

  // Merge template properties with existing frontmatter, preserving existing values.
  const finalFm = Object.assign({}, templateFm || {}, currentFm || {});
  finalFm.slug = slug;
  finalFm.project = project;

  const currentBody = splitFrontmatter(currentText).body;
  const finalBody = currentBody.trim() ? currentBody : templateBody;
  const out = composeNote(finalFm, finalBody);

  await app.vault.modify(activeFile, out);
  notice(`Applied template: ${picked.path}`);
};

function collectTemplates(app) {
  const roots = ["_common/template", "_common/templates", "templates"];
  const unique = new Map();
  const files = app.vault.getMarkdownFiles();

  for (const file of files) {
    const path = String(file.path || "");
    for (const rootPath of roots) {
      const prefix = `${rootPath}/`;
      if (!path.startsWith(prefix)) continue;
      if (!unique.has(path)) {
        const rel = path.slice(prefix.length);
        unique.set(path, {
          file,
          path,
          label: `${rootPath}: ${rel || file.name}`,
        });
      }
      break;
    }
  }

  return [...unique.values()].sort((a, b) => a.path.localeCompare(b.path));
}

function splitFrontmatter(raw) {
  const text = String(raw || "").replace(/\r\n?/g, "\n");
  if (!text.startsWith("---\n")) return { frontmatter: {}, body: text };

  const end = text.indexOf("\n---\n", 4);
  if (end === -1) return { frontmatter: {}, body: text };

  const yamlRaw = text.slice(4, end);
  const body = text.slice(end + 5);
  const parseYaml = globalThis?.obsidian?.parseYaml;
  if (typeof parseYaml === "function") {
    try {
      const parsed = parseYaml(yamlRaw);
      return { frontmatter: parsed && typeof parsed === "object" ? parsed : {}, body };
    } catch (_) {
      return { frontmatter: {}, body };
    }
  }
  return { frontmatter: {}, body };
}

function composeNote(frontmatter, body) {
  const stringifyYaml = globalThis?.obsidian?.stringifyYaml;
  let yaml = "";
  if (typeof stringifyYaml === "function") {
    yaml = String(stringifyYaml(frontmatter || {})).trimEnd();
  } else {
    yaml = toYamlObject(frontmatter || {}, 0).join("\n");
  }

  // Keep slug as a plain scalar (no quotes) for predictable note IDs.
  yaml = yaml.replace(
    /^(\s*slug:\s*)['"]([^'"\n]+)['"]\s*$/m,
    (_, prefix, value) => `${prefix}${value}`,
  );

  const textBody = String(body || "");
  return `---\n${yaml}\n---\n\n${textBody}`.replace(/\s+$/, "\n");
}

function isPlainObject(value) {
  return Object.prototype.toString.call(value) === "[object Object]";
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
  const s = String(value);
  if (!s.trim()) return '""';
  if (/[:#\-\[\]\{\}\n]/.test(s)) return JSON.stringify(s);
  return s;
}

function normalizeFrontmatter(fm) {
  if (!fm || typeof fm !== "object") return {};
  const out = {};
  for (const [k, v] of Object.entries(fm)) {
    if (k === "position") continue;
    out[k] = v;
  }
  return out;
}

function containsDataview(text) {
  return /```(?:dataview|dataviewjs)\b/i.test(String(text || ""));
}

function buildSlug(filePath) {
  const parts = String(filePath || "").split("/").filter(Boolean);
  const file = parts.length ? parts[parts.length - 1] : "untitled.md";
  const parent = parts.length > 1 ? parts[parts.length - 2] : "";
  const base = file.replace(/\.md$/i, "");
  const left = toKebab(parent);
  const right = toKebab(base);
  return left ? `${left}-${right}` : right;
}

function toKebab(s) {
  return String(s || "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/-{2,}/g, "-");
}

async function resolveProjectName(app) {
  // Prefer project name from vault-level ingest config when available.
  try {
    const ingestPath = ".ingest.yml";
    const exists = await app.vault.adapter.exists(ingestPath);
    if (exists) {
      const raw = await app.vault.adapter.read(ingestPath);
      const m = raw.match(/^\s*project:\s*["']?([^"'\n#]+?)["']?\s*$/m);
      if (m && m[1] && m[1].trim()) return m[1].trim();
    }
  } catch (_) {
    // Fallback below.
  }

  // For mnemonic vault layouts like <project_name>/<mnemonic>, use parent folder.
  try {
    const adapter = app.vault?.adapter;
    const basePath =
      (typeof adapter?.getBasePath === "function" && adapter.getBasePath()) ||
      adapter?.basePath ||
      "";
    if (basePath) {
      const path = require("path");
      const vaultName = app.vault.getName ? String(app.vault.getName()) : "";
      const parentName = path.basename(path.dirname(basePath));
      if (
        parentName &&
        (!vaultName || parentName.toLowerCase() !== vaultName.toLowerCase())
      ) {
        return parentName;
      }
    }
  } catch (_) {
    // Final fallback below.
  }

  return app.vault.getName ? String(app.vault.getName()) : "project";
}

function notice(message, timeout = 8000) {
  if (typeof Notice === "function") new Notice(message, timeout);
  console.log(message);
}

function fail(message) {
  const text = `Apply Template failed: ${message}`;
  if (typeof Notice === "function") new Notice(text, 10000);
  console.error(text);
}
