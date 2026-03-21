const path = require("path");

const DEFAULT_TEMPLATES_FOLDER = "_control/templates";
const DESTINATION_FOLDER_BY_TEMPLATE = {
  content: "contents",
  instruction: "instructions",
  topic: "topics",
};

async function createNote(params = {}) {
  const app = resolveApp(params.app);
  const qa = params.quickAddApi || params.quickAdd || null;

  if (!app || !app.vault || !app.workspace) {
    throw new Error("Obsidian context not available.");
  }

  const runtime = loadCreateNoteRuntime(app, params.runtimeHelper);
  const anchorFile = app.workspace.getActiveFile?.();
  const templates = await listTemplates(app, {
    runtime,
    templatesFolder: params.templatesFolder || params.templateFolder,
  });
  const template = await chooseTemplate(app, templates, qa, params);
  if (!template?.file?.path) {
    throw new Error("Template selection was cancelled.");
  }

  const rawTitle = await promptNoteTitle(qa, params);
  const title = normalizeNoteTitle(rawTitle);
  if (!title) {
    throw new Error("Note title is required.");
  }

  const folder = getDestinationFolderFromTemplate(template.file, params);

  let createdFile = null;
  let leaf = null;

  try {
    createdFile = await createNoteFromTemplate({
      app,
      qa,
      folder,
      templateFile: template.file,
      title,
    });
    leaf = await openCreatedNote({ app, file: createdFile });
    await runEmbeddedTemplateMacro({ app, file: createdFile, params, runtime });
    const validation = await validateCreatedNote({ app, file: createdFile, runtime });

    return {
      path: validation.path,
      slug: validation.slug,
      template: template.file.path,
    };
  } catch (error) {
    if (createdFile) {
      await rollbackCreatedNote({
        app,
        anchorFile,
        file: createdFile,
        leaf,
        reason: error?.message || String(error),
      });
    }
    throw error;
  }
}

module.exports = createNote;
module.exports._test = {
  chooseTemplate,
  confirmAction,
  createNoteFromTemplate,
  ensureDestinationFolder,
  getDestinationFolderFromTemplate,
  listTemplates,
  normalizeNoteTitle,
  promptNoteTitle,
  rollbackCreatedNote,
  validateCreatedNote,
};

function resolveApp(candidateApp) {
  if (candidateApp?.vault?.adapter && candidateApp?.workspace) {
    return candidateApp;
  }

  if (typeof window !== "undefined" && window?.app?.vault?.adapter && window?.app?.workspace) {
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

function loadCreateNoteRuntime(app, overrideRuntime) {
  if (overrideRuntime) {
    return overrideRuntime;
  }

  return require(path.join(getVaultBasePath(app), "_control", "scripts", "create_note_runtime.js"));
}

function notice(message, timeout = 8000) {
  if (typeof Notice === "function") {
    new Notice(message, timeout);
  }
  console.log(message);
}

async function listTemplates(app, options = {}) {
  const runtime = options.runtime || loadCreateNoteRuntime(app);
  const templatesFolder = normalizeFolder(
    options.templatesFolder || options.templateFolder || DEFAULT_TEMPLATES_FOLDER,
  );
  const prefix = templatesFolder ? `${templatesFolder}/` : "";

  const candidates = app.vault
    .getMarkdownFiles()
    .filter((file) => file?.extension === "md")
    .filter((file) => String(file.path || "").startsWith(prefix))
    .filter((file) => !String(file.basename || "").startsWith("."))
    .filter((file) => !String(file.basename || "").startsWith("_"))
    .sort((left, right) => left.path.localeCompare(right.path));

  const runnable = [];
  for (const file of candidates) {
    const text = await app.vault.cachedRead(file);
    if (runtime.countEmbeddedRuntimeBlocks(text) !== 1) {
      continue;
    }

    runnable.push({
      file,
      label: formatTemplateLabel(file.basename),
    });
  }

  if (runnable.length === 0) {
    throw new Error(`No runnable templates found in ${templatesFolder}.`);
  }

  return runnable;
}

async function chooseTemplate(app, templates, qa, params = {}) {
  const requested = normalizeString(params.template || "");
  if (requested) {
    const requestedKeys = new Set(
      [
        requested,
        requested.replace(/\.md$/i, ""),
        requested.endsWith(".md") ? requested : `${requested}.md`,
      ]
        .map((value) => normalizeString(value).toLowerCase())
        .filter(Boolean),
    );

    for (const template of templates) {
      const templatePath = normalizeString(template?.file?.path);
      const templateBase = normalizeString(template?.file?.basename);
      const templateLabel = normalizeString(template?.label);
      const candidates = [
        templatePath,
        templatePath.replace(/\.md$/i, ""),
        templateBase,
        templateBase.replace(/\.md$/i, ""),
        templateLabel,
      ]
        .map((value) => value.toLowerCase())
        .filter(Boolean);

      if (candidates.some((value) => requestedKeys.has(value))) {
        return template;
      }
    }

    throw new Error(`Template not found: ${requested}`);
  }

  if (qa && typeof qa.suggester === "function") {
    return qa.suggester(
      templates.map((item) => item.label),
      templates,
      "Pick template",
    );
  }

  if (templates.length === 1) {
    return templates[0];
  }

  throw new Error("Template selection requires QuickAdd suggester support.");
}

async function promptNoteTitle(qa, params = {}) {
  const preset = normalizeString(params.title || params.name || "");
  if (preset) {
    return preset;
  }

  if (qa && typeof qa.inputPrompt === "function") {
    return qa.inputPrompt("Note title", preset, preset);
  }

  if (qa && typeof qa.requestInputs === "function") {
    const values = await qa.requestInputs([
      {
        id: "note_title",
        label: "Note title",
        type: "text",
        defaultValue: preset,
      },
    ]);
    return values.note_title || "";
  }

  if (typeof window !== "undefined" && typeof window.prompt === "function") {
    return window.prompt("Note title", preset);
  }

  return "";
}

function getDestinationFolderFromTemplate(templateFile, params = {}) {
  const requestedFolder = normalizeFolder(params.destinationFolder || params.folder || "");
  if (requestedFolder) {
    return requestedFolder;
  }

  const templateName = normalizeString(templateFile?.basename || "").toLowerCase();
  if (!templateName) {
    throw new Error("Template file is required to choose the destination folder.");
  }

  return normalizeFolder(
    DESTINATION_FOLDER_BY_TEMPLATE[templateName] || pluralizeFolderName(templateName),
  );
}

function pluralizeFolderName(value) {
  const normalized = normalizeString(value).toLowerCase();
  if (!normalized) {
    return "";
  }
  if (normalized.endsWith("s")) {
    return normalized;
  }
  return `${normalized}s`;
}

async function createNoteFromTemplate({ app, qa, templateFile, folder, title }) {
  const safeTitle = normalizeNoteTitle(title);
  if (!safeTitle) {
    throw new Error("Note title is required.");
  }

  if (!templateFile?.path) {
    throw new Error("Template file is required.");
  }

  const templateText = await app.vault.cachedRead(templateFile);
  const normalizedFolder = normalizeFolder(folder);
  await ensureDestinationFolder({ app, qa, folder: normalizedFolder, templateFile });
  const notePath = normalizedFolder ? `${normalizedFolder}/${safeTitle}.md` : `${safeTitle}.md`;

  if (await pathExists(app, notePath)) {
    throw new Error(`File already exists: ${notePath}`);
  }

  return app.vault.create(notePath, templateText);
}

async function ensureDestinationFolder({ app, qa, folder, templateFile } = {}) {
  const normalizedFolder = normalizeFolder(folder);
  if (!normalizedFolder) {
    return "";
  }

  if (await pathExists(app, normalizedFolder)) {
    return normalizedFolder;
  }

  const templateLabel = formatTemplateLabel(templateFile?.basename || normalizedFolder);
  const confirmed = await confirmAction(
    qa,
    "Create destination folder?",
    `Template ${templateLabel} writes new notes to ${normalizedFolder}. Create that folder now?`,
  );
  if (!confirmed) {
    throw new Error(`Destination folder does not exist: ${normalizedFolder}`);
  }

  await createFolder(app, normalizedFolder);
  return normalizedFolder;
}

async function pathExists(app, targetPath) {
  const normalizedPath = normalizeFolder(targetPath);
  if (!normalizedPath) {
    return true;
  }

  const existing = app.vault.getAbstractFileByPath?.(normalizedPath);
  if (existing) {
    return true;
  }

  if (typeof app.vault.adapter?.exists === "function") {
    return Boolean(await app.vault.adapter.exists(normalizedPath));
  }

  return false;
}

async function createFolder(app, folder) {
  if (typeof app.vault.createFolder === "function") {
    await app.vault.createFolder(folder);
    return;
  }

  if (typeof app.vault.adapter?.mkdir === "function") {
    await app.vault.adapter.mkdir(folder);
    return;
  }

  throw new Error(`Could not create folder: ${folder}`);
}

async function confirmAction(qa, title, message) {
  if (qa && typeof qa.yesNoPrompt === "function") {
    try {
      return await qa.yesNoPrompt(title, message);
    } catch (_error) {
      return false;
    }
  }

  if (typeof window !== "undefined" && typeof window.confirm === "function") {
    return window.confirm(`${title}\n\n${message}`);
  }

  return false;
}

async function openCreatedNote({ app, file }) {
  const leaf = app.workspace.getLeaf?.(true) || app.workspace.activeLeaf || null;
  if (leaf && typeof leaf.openFile === "function") {
    await leaf.openFile(file);
  }
  return leaf;
}

async function runEmbeddedTemplateMacro({ app, file, params = {}, runtime }) {
  const helper = runtime || loadCreateNoteRuntime(app);
  return helper.executeEmbeddedTemplateMacro({ app, file, params });
}

async function validateCreatedNote({ app, file, runtime }) {
  const helper = runtime || loadCreateNoteRuntime(app);
  return helper.validateCreatedNote({ app, file });
}

async function rollbackCreatedNote({ app, anchorFile, file, leaf, reason }) {
  const helper = loadCreateNoteRuntime(app);

  try {
    const openLeaf = leaf || app.workspace.activeLeaf || null;
    if (anchorFile && openLeaf && typeof openLeaf.openFile === "function") {
      await openLeaf.openFile(anchorFile);
    }
  } catch (_error) {
    // Best effort: deleting the malformed file is more important than leaf restoration.
  }

  try {
    await helper.deleteFile({ app, file });
    notice(`Create note aborted: ${reason}. Deleted ${file.path}.`, 10000);
  } catch (rollbackError) {
    const rollbackReason = rollbackError?.message || String(rollbackError);
    notice(
      `Create note aborted: ${reason}. Rollback also failed for ${file.path}: ${rollbackReason}`,
      12000,
    );
    throw rollbackError;
  }
}

function normalizeNoteTitle(value) {
  return normalizeString(value)
    .replace(/\.md$/i, "")
    .replace(/[\\/:*?"<>|#[\]^]/g, " ")
    .replace(/\s+/g, " ")
    .replace(/\.+$/g, "")
    .trim();
}

function normalizeFolder(value) {
  const normalized = normalizeString(value).replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
  return normalized === "." ? "" : normalized;
}

function normalizeString(value) {
  return String(value || "").trim();
}

function formatTemplateLabel(filename) {
  return normalizeString(filename)
    .replace(/\.md$/i, "")
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}
