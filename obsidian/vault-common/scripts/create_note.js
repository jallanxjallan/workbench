module.exports = async (params = {}) => {
  const app = resolveApp(params.app);

  if (!app || !app.vault || !app.vault.adapter) {
    return notice("Obsidian context not available.");
  }

  const registryPath =
    params.registryPath || (await resolveEditorialRegistryPath(app));
  const dialogHandler = params.showCreateNoteDialog || showCreateNoteDialog;

  if (!registryPath) {
    return notice("Editorial registry path not found in _vault_registry.");
  }

  let registry;
  try {
    registry = await loadJson(app, registryPath);
  } catch (error) {
    console.error("Registry load error:", registryPath, error);
    const reason = error && error.message ? error.message : String(error);
    return notice(`Failed to load registry: ${reason}`);
  }

  let model;
  try {
    model = buildRegistryModel(registry);
  } catch (error) {
    return notice(error.message || "Invalid registry format.");
  }

  const selection = await dialogHandler(model);
  if (!selection) {
    return notice("Create note cancelled");
  }

  const title = (selection.title || "").trim();
  if (!title) {
    return notice("Title is required.");
  }

  const classId = selection.classId || model.defaults.classId;
  const classItem = model.classById.get(classId);
  const mappedFolder = classItem
    ? pickClassFolder(classItem.folders, model.folderById)
    : null;

  const folder = model.folderById.get(
    selection.folderId || (mappedFolder && mappedFolder.id) || model.defaults.folderId
  );

  const templateId =
    selection.templateId ||
    (classItem && classItem.template) ||
    model.defaults.templateId;
  const template = model.templateById.get(templateId);

  if (!folder || !classItem || !template) {
    return notice("Invalid selection.");
  }

  const slug = titleToSlug(title);
  const fileName = titleToFileName(title);
  const notePath = buildNotePath(folder.path, fileName);

  if (await app.vault.adapter.exists(notePath)) {
    return notice(`File already exists: ${notePath}`);
  }

  try {
    await ensureFolderExists(app, folder.path);
    const templateRaw = await app.vault.adapter.read(template.path);
    const withReplacements = applyTemplateReplacements(templateRaw, {
      className: classItem.id,
      title,
      slug,
    });
    const content = stripFrontmatterTitleField(withReplacements);

    const file = await app.vault.create(notePath, content);
    if (app.workspace && typeof app.workspace.getLeaf === "function") {
      await app.workspace.getLeaf(true).openFile(file);
    }

    return notice(`Created note: ${notePath}`);
  } catch (error) {
    return notice(`Failed to create note: ${error.message || String(error)}`);
  }
};

async function loadJson(app, path) {
  const raw = await readText(app, path);

  try {
    return JSON.parse(raw);
  } catch (error) {
    console.error("Registry JSON parse error:", path, error);
    notice("Registry JSON error. See console.");
    throw error;
  }
}

async function resolveEditorialRegistryPath(app) {
  const fallbackPath = "_common/registries/editorial.json";
  try {
    const vaultRegistry = await loadVaultRegistry(app);
    const fromMap =
      vaultRegistry &&
      vaultRegistry.registry_paths &&
      vaultRegistry.registry_paths.editorial;
    const fromFlat = vaultRegistry && vaultRegistry.editorial_registry_json;
    const selected = String(fromMap || fromFlat || "").trim();
    if (selected) {
      return selected;
    }
  } catch (error) {
    console.warn("create_note: unable to resolve _vault_registry path.", error);
  }

  return fallbackPath;
}

async function loadVaultRegistry(app) {
  const raw = await app.vault.adapter.read("_vault_registry");
  const text = String(raw || "").trim();
  if (!text) {
    return {};
  }

  const firstLine = text.split(/\r?\n/).find((line) => line.trim());
  if (!firstLine) {
    return {};
  }

  try {
    return JSON.parse(firstLine);
  } catch (error) {
    return JSON.parse(text);
  }
}

async function readText(app, path) {
  try {
    return await app.vault.adapter.read(path);
  } catch (error) {
    if (!isAbsolutePath(path)) {
      throw error;
    }

    const nodeRequire = resolveRequire();
    if (!nodeRequire) {
      throw error;
    }

    const fs = nodeRequire("fs");
    if (!fs || !fs.promises || typeof fs.promises.readFile !== "function") {
      throw error;
    }
    return fs.promises.readFile(path, "utf8");
  }
}

function resolveRequire() {
  if (typeof require === "function") {
    return require;
  }
  if (typeof window !== "undefined" && typeof window.require === "function") {
    return window.require;
  }
  return null;
}

function isAbsolutePath(path) {
  return typeof path === "string" && path.startsWith("/");
}

function resolveApp(candidateApp) {
  if (candidateApp && candidateApp.vault && candidateApp.vault.adapter) {
    return candidateApp;
  }

  const globalApp = typeof window !== "undefined" ? window.app : null;
  if (globalApp && globalApp.vault && globalApp.vault.adapter) {
    return globalApp;
  }

  return candidateApp;
}

function buildRegistryModel(registry = {}) {
  const folders = sortByScore(
    Object.entries(registry.folders || {}).map(([id, value]) => ({
      id,
      path: normalizeFolderPath(value && value.path),
      score: toScore(value && value.score),
    }))
  );

  const classes = sortByScore(
    Object.entries(registry.classes || {}).map(([id, value]) => ({
      id,
      template: String((value && value.template) || "").trim(),
      folders: Array.isArray(value && value.folders)
        ? value.folders.map((item) => String(item))
        : [],
      score: toScore(value && value.score),
    }))
  );

  const templates = sortByScore(
    Object.entries(registry.templates || {}).map(([id, value]) => ({
      id,
      path: String((value && value.path) || "").trim(),
      score: toScore(value && value.score),
    }))
  );

  if (!folders.length) {
    throw new Error("Registry has no folders.");
  }

  if (!classes.length) {
    throw new Error("Registry has no classes.");
  }

  if (!templates.length) {
    throw new Error("Registry has no templates.");
  }

  const folderById = new Map(folders.map((item) => [item.id, item]));
  const classById = new Map(classes.map((item) => [item.id, item]));
  const templateById = new Map(templates.map((item) => [item.id, item]));

  for (const item of folders) {
    if (!item.path) {
      throw new Error(`Folder "${item.id}" is missing path.`);
    }
  }

  for (const item of classes) {
    if (!item.template) {
      throw new Error(`Class "${item.id}" is missing template.`);
    }
    if (!templateById.has(item.template)) {
      throw new Error(`Class "${item.id}" template "${item.template}" not found.`);
    }
  }

  for (const item of templates) {
    if (!item.path) {
      throw new Error(`Template "${item.id}" is missing path.`);
    }
  }

  return {
    folders,
    classes,
    templates,
    folderById,
    classById,
    templateById,
    defaults: {
      folderId: folders[0].id,
      classId: classes[0].id,
      templateId: templates[0].id,
    },
  };
}

function sortByScore(items) {
  return [...items].sort((left, right) => {
    if (right.score !== left.score) {
      return right.score - left.score;
    }
    return left.id.localeCompare(right.id);
  });
}

function toScore(score) {
  const parsed = Number(score);
  return Number.isFinite(parsed) ? parsed : 0;
}

function normalizeFolderPath(value) {
  return String(value || "")
    .trim()
    .replace(/^\/+|\/+$/g, "");
}

function titleToSlug(title) {
  const slug = String(title || "")
    .trim()
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");

  return slug || "untitled";
}

function titleToFileName(title) {
  const fileStem = String(title || "")
    .trim()
    .replace(/\.md$/i, "")
    .replace(/[\\/]/g, "-")
    .trim();
  return fileStem || "Untitled";
}

function buildNotePath(folderPath, fileStem) {
  const safeFolder = normalizeFolderPath(folderPath);
  if (!safeFolder) {
    return `${fileStem}.md`;
  }
  return `${safeFolder}/${fileStem}.md`;
}

function applyTemplateReplacements(templateRaw, values) {
  return String(templateRaw || "")
    .replace(/__CLASS__/g, () => values.className)
    .replace(/__TITLE__/g, () => values.title)
    .replace(/__SLUG__/g, () => values.slug);
}

function stripFrontmatterTitleField(content) {
  const text = String(content || "");
  const lines = text.split("\n");

  if (!lines.length || lines[0].trim() !== "---") {
    return text;
  }

  let endIndex = -1;
  for (let index = 1; index < lines.length; index += 1) {
    if (lines[index].trim() === "---") {
      endIndex = index;
      break;
    }
  }

  if (endIndex === -1) {
    return text;
  }

  const frontmatterLines = lines
    .slice(1, endIndex)
    .filter((line) => !/^\s*title\s*:/.test(line));

  return [
    "---",
    ...frontmatterLines,
    "---",
    ...lines.slice(endIndex + 1),
  ].join("\n");
}

async function ensureFolderExists(app, folderPath) {
  const normalized = normalizeFolderPath(folderPath);
  if (!normalized) {
    return;
  }

  const parts = normalized.split("/");
  let current = "";
  for (const part of parts) {
    current = current ? `${current}/${part}` : part;
    if (!app.vault.getAbstractFileByPath(current)) {
      await app.vault.createFolder(current);
    }
  }
}

async function showCreateNoteDialog(model) {
  if (typeof document === "undefined") {
    throw new Error("Dialog unavailable in this environment.");
  }

  return new Promise((resolve) => {
    const { folders, classes, templates, classById, folderById, templateById, defaults } =
      model;

    const overlay = document.createElement("div");
    overlay.innerHTML = buildDialogHtml({ folders, classes, templates, defaults });
    Object.assign(overlay.style, {
      position: "fixed",
      inset: "0",
      backgroundColor: "rgba(0, 0, 0, 0.45)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: "9999",
      padding: "24px",
      boxSizing: "border-box",
    });

    const panel = overlay.querySelector("[data-create-note-panel]");
    const form = overlay.querySelector("[data-create-note-form]");
    const titleInput = overlay.querySelector("[data-create-note-title]");

    if (!panel || !form || !titleInput) {
      resolve(null);
      return;
    }

    Object.assign(panel.style, {
      width: "100%",
      maxWidth: "560px",
      borderRadius: "12px",
      border: "1px solid var(--background-modifier-border)",
      background: "var(--background-primary)",
      color: "var(--text-normal)",
      padding: "18px",
      boxSizing: "border-box",
      boxShadow: "0 20px 50px rgba(0, 0, 0, 0.35)",
    });

    document.body.appendChild(overlay);
    titleInput.focus();

    const close = (result) => {
      overlay.remove();
      resolve(result);
    };

    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) {
        close(null);
      }
    });

    overlay.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        close(null);
      }
    });

    form.addEventListener("change", (event) => {
      const target = event.target;
      if (!target || target.name !== "class" || !target.checked) {
        return;
      }

      const selectedClass = classById.get(target.value);
      if (!selectedClass) {
        return;
      }

      if (selectedClass.template && templateById.has(selectedClass.template)) {
        setChecked(form, "template", selectedClass.template);
      }

      const preferredFolder = pickClassFolder(selectedClass.folders, folderById);
      if (preferredFolder) {
        setChecked(form, "folder", preferredFolder.id);
      }
    });

    form.addEventListener("submit", (event) => {
      event.preventDefault();

      const title = String(titleInput.value || "").trim();
      if (!title) {
        titleInput.focus();
        return;
      }

      close({
        folderId: getCheckedValue(form, "folder") || defaults.folderId,
        classId: getCheckedValue(form, "class") || defaults.classId,
        templateId: getCheckedValue(form, "template") || defaults.templateId,
        title,
      });
    });
  });
}

function buildDialogHtml({ folders, classes, templates, defaults }) {
  return `
    <div data-create-note-panel>
      <form data-create-note-form>
        <h2 style="margin: 0 0 12px 0;">Create Note</h2>
        ${renderRadioGroup("Folder", "folder", folders, defaults.folderId)}
        ${renderRadioGroup("Class", "class", classes, defaults.classId)}
        ${renderRadioGroup("Template", "template", templates, defaults.templateId)}
        <label style="display: block; margin-top: 12px; font-weight: 600;">
          Title
          <input
            data-create-note-title
            type="text"
            style="display:block; width:100%; margin-top:6px; box-sizing:border-box;"
            placeholder="my_new_note"
          />
        </label>
        <div style="margin-top: 14px; display: flex; justify-content: flex-end;">
          <button type="submit">Create</button>
        </div>
      </form>
    </div>
  `;
}

function renderRadioGroup(label, name, items, selectedId) {
  const options = items
    .map((item) => {
      const checked = item.id === selectedId ? "checked" : "";
      return `
        <label style="display:block; margin: 4px 0;">
          <input type="radio" name="${escapeHtml(name)}" value="${escapeHtml(item.id)}" ${checked} />
          ${escapeHtml(item.id)}
        </label>
      `;
    })
    .join("");

  return `
    <fieldset style="margin: 8px 0; padding: 8px 10px;">
      <legend>${escapeHtml(label)}</legend>
      ${options}
    </fieldset>
  `;
}

function getCheckedValue(form, name) {
  const checked = form.querySelector(`input[name="${name}"]:checked`);
  return checked ? checked.value : "";
}

function setChecked(form, name, value) {
  const input = form.querySelector(`input[name="${name}"][value="${cssEscape(value)}"]`);
  if (input) {
    input.checked = true;
  }
}

function pickClassFolder(folderIds, folderById) {
  if (!Array.isArray(folderIds) || !folderIds.length) {
    return null;
  }

  const candidates = folderIds
    .map((id) => folderById.get(String(id)))
    .filter(Boolean)
    .sort((left, right) => {
      if (right.score !== left.score) {
        return right.score - left.score;
      }
      return left.id.localeCompare(right.id);
    });

  return candidates[0] || null;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function cssEscape(value) {
  return String(value).replace(/\\/g, "\\\\").replace(/"/g, '\\"');
}

function notice(message, timeout = 8000) {
  if (typeof Notice === "function") {
    new Notice(message, timeout);
  }
  console.log(message);
}

module.exports.__test = {
  applyTemplateReplacements,
  buildNotePath,
  buildRegistryModel,
  pickClassFolder,
  sortByScore,
  stripFrontmatterTitleField,
  titleToFileName,
  titleToSlug,
};
