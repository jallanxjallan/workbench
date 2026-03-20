const ALPHABET = "abcdefghijklmnopqrstuvwxyz";

function randomAlpha(length = 6) {
  let output = "";
  for (let index = 0; index < length; index += 1) {
    const offset = Math.floor(Math.random() * ALPHABET.length);
    output += ALPHABET[offset];
  }
  return output;
}

function defaultGenerateSlug(domain) {
  const normalized = typeof domain === "string" && domain.trim()
    ? domain.trim().toLowerCase()
    : "gbl";
  return `${normalized}.untitled.${randomAlpha(6)}`;
}

function loadGenerateSlug() {
  try {
    const helper = require("./slug");
    if (helper && typeof helper.generate_slug === "function") {
      return helper.generate_slug;
    }
  } catch (_error) {
    // Fall back to the local generator if the helper is unavailable.
  }
  return defaultGenerateSlug;
}

const generateSlug = loadGenerateSlug();

const NOTE_TYPES = {
  gbl: {
    label: "Instruction (gbl)",
    domain: "gbl",
    folder: "instructions",
    scope: "global",
  },
  cxt: {
    label: "Instruction (cxt)",
    domain: "cxt",
    folder: "instructions",
    scope: "context",
  },
  pkg: {
    label: "Package (pkg)",
    domain: "pkg",
    folder: "packages",
    scope: null,
  },
};

function buildContent(kind, slug) {
  if (kind === "pkg") {
    return [
      "---",
      `slug: ${slug}`,
      "type: package",
      "version: 1",
      "",
      "instructions:",
      "  - __CURSOR__",
      "",
      "pipeline:",
      "  - step:",
      "---",
      "",
      "# Notes",
      "",
    ].join("\n");
  }

  const config = NOTE_TYPES[kind];
  return [
    "---",
    `slug: ${slug}`,
    "type: instruction",
    `scope: ${config.scope}`,
    "version: 1",
    "---",
    "",
    "# Instruction",
    "",
    "__CURSOR__",
  ].join("\n");
}

async function ensureFolder(app, folderPath) {
  if (app.vault.getAbstractFileByPath(folderPath)) {
    return;
  }
  await app.vault.createFolder(folderPath);
}

async function openFile(app, file) {
  const leaf = app.workspace.getLeaf(true);
  await leaf.openFile(file);
  return leaf;
}

function removeCursorMarker(value) {
  return value.replace("__CURSOR__", "");
}

async function placeCursor(leaf) {
  const view = leaf?.view;
  const editor = view && "editor" in view ? view.editor : null;
  if (!editor) {
    return;
  }

  const line = editor.lastLine();
  editor.setCursor({ line, ch: 0 });
}

async function createUniquePath(app, folder, domain) {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    const slug = generateSlug(domain);
    const path = `${folder}/${slug}.md`;
    if (!app.vault.getAbstractFileByPath(path)) {
      return { slug, path };
    }
  }

  const fallbackSlug = defaultGenerateSlug(domain);
  return { slug: fallbackSlug, path: `${folder}/${fallbackSlug}.md` };
}

module.exports = async (params) => {
  const { app, quickAddApi, obsidian } = params;
  const { Notice } = obsidian;

  try {
    const kind = await quickAddApi.suggester(
      [
        "Instruction (gbl)",
        "Instruction (cxt)",
        "Package (pkg)",
      ],
      ["gbl", "cxt", "pkg"]
    );
    if (!kind) {
      return;
    }

    const config = NOTE_TYPES[kind];
    await ensureFolder(app, config.folder);

    const { slug, path } = await createUniquePath(app, config.folder, config.domain);
    const content = removeCursorMarker(buildContent(kind, slug));
    const file = await app.vault.create(path, content);
    const leaf = await openFile(app, file);
    await placeCursor(leaf);

    params.variables = params.variables || {};
    params.variables.slug = slug;
    params.variables.file_path = path;

    new Notice(`Created ${config.label.toLowerCase()}: ${slug}`);
  } catch (error) {
    const message = error && error.message ? error.message : String(error);
    new Notice(`create_note failed: ${message}`);
    throw error;
  }
};
