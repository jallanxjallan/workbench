```dataviewjs
(() => {
  const DEFAULT_DISPATCH_MACRO = "Dispatch: Apply Template To Files";

  const container = dv?.container ?? this?.container;
  if (!container) {
    if (typeof Notice === "function") new Notice("List Folder: no render container.");
    return;
  }
  container.empty();

  const current = dv.current?.() || {};
  const dispatchMacro = String(
    current.dispatch_macro || DEFAULT_DISPATCH_MACRO,
  ).trim();

  let selectedFolder = normalizeFolderPath(
    String(current.folder_path || current.folder || current?.file?.folder || ""),
  );
  const selectedFiles = new Set();

  const toolbar = container.createDiv();
  Object.assign(toolbar.style, {
    display: "flex",
    gap: "0.75rem",
    flexWrap: "wrap",
    alignItems: "center",
    marginBottom: "0.5rem",
  });

  const folderLabel = toolbar.createEl("strong", {
    text: `Folder: ${displayFolder(selectedFolder)}`,
  });
  const chooseFolderBtn = toolbar.createEl("button", { text: "Select Folder" });
  const selectAllBtn = toolbar.createEl("button", { text: "Select All" });
  const clearBtn = toolbar.createEl("button", { text: "Clear" });

  const statusLine = container.createDiv();
  Object.assign(statusLine.style, { marginBottom: "0.4rem" });

  const list = container.createEl("ul");
  Object.assign(list.style, {
    listStyle: "none",
    margin: "0 0 0.8rem 0",
    padding: "0",
  });

  // Bottom command button required by the workflow.
  const applyBtn = container.createEl("button", {
    text: "Apply Template To Selected",
  });

  let currentRows = [];

  chooseFolderBtn.addEventListener("click", chooseFolder);
  selectAllBtn.addEventListener("click", () => {
    selectedFiles.clear();
    for (const row of currentRows) selectedFiles.add(row.path);
    for (const checkbox of list.querySelectorAll("input[type='checkbox']")) {
      checkbox.checked = true;
    }
    renderStatus();
  });
  clearBtn.addEventListener("click", () => {
    selectedFiles.clear();
    for (const checkbox of list.querySelectorAll("input[type='checkbox']")) {
      checkbox.checked = false;
    }
    renderStatus();
  });
  applyBtn.addEventListener("click", applyTemplateToSelected);

  renderRows();

  async function chooseFolder() {
    const folders = collectFolderPaths(app);
    if (folders.length === 0) {
      if (typeof Notice === "function") new Notice("No folders found.");
      return;
    }

    const quickAddApi = app?.plugins?.plugins?.quickadd?.api;
    let picked = "";
    if (quickAddApi && typeof quickAddApi.suggester === "function") {
      picked = await quickAddApi.suggester(folders, folders, "Pick folder");
    } else {
      picked = window.prompt("Folder path", selectedFolder || "") || "";
    }

    if (picked === null || typeof picked === "undefined") return;

    selectedFolder = normalizeFolderPath(String(picked));
    selectedFiles.clear();
    folderLabel.setText(`Folder: ${displayFolder(selectedFolder)}`);
    renderRows();
  }

  function renderRows() {
    list.empty();
    currentRows = collectRowsForFolder(selectedFolder);

    if (currentRows.length === 0) {
      statusLine.setText(`No markdown files found in ${displayFolder(selectedFolder)}.`);
      return;
    }

    for (const rowData of currentRows) {
      const row = list.createEl("li");
      Object.assign(row.style, {
        display: "flex",
        alignItems: "center",
        gap: "0.5rem",
        marginBottom: "0.35rem",
      });

      const checkbox = row.createEl("input", { type: "checkbox" });
      checkbox.checked = selectedFiles.has(rowData.path);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) selectedFiles.add(rowData.path);
        else selectedFiles.delete(rowData.path);
        renderStatus();
      });

      const linkTarget = rowData.path.replace(/\.md$/i, "");
      const link = row.createEl("a", {
        text: rowData.title,
        href: linkTarget,
        cls: "internal-link",
      });
      link.setAttr("data-href", linkTarget);

      const meta = row.createEl("small", { text: `(${rowData.path})` });
      Object.assign(meta.style, { opacity: "0.7" });
    }

    renderStatus();
  }

  function renderStatus() {
    const total = currentRows.length;
    const selected = selectedFiles.size;
    statusLine.setText(`${selected} selected / ${total} file${total === 1 ? "" : "s"}.`);
  }

  async function applyTemplateToSelected() {
    const selectedRelativePaths = Array.from(selectedFiles.values());
    if (selectedRelativePaths.length === 0) {
      if (typeof Notice === "function") new Notice("No files selected.");
      return;
    }
    const filepaths = toAbsolutePaths(selectedRelativePaths, app);
    if (filepaths.length === 0) {
      if (typeof Notice === "function") {
        new Notice("Could not resolve absolute paths for selected files.");
      }
      return;
    }

    const quickAddApi = app?.plugins?.plugins?.quickadd?.api;
    if (!quickAddApi || typeof quickAddApi.executeChoice !== "function") {
      if (typeof Notice === "function") {
        new Notice("QuickAdd API not available for apply_template.");
      }
      return;
    }

    globalThis.__wkbTemplateFilepaths = filepaths;
    try {
      await quickAddApi.executeChoice(dispatchMacro, { filepaths });
    } catch (error) {
      const message = error?.message || String(error);
      if (typeof Notice === "function") {
        new Notice(`Apply template failed: ${message}`);
      }
      console.error(error);
    }
  }
})();

function normalizeFolderPath(path) {
  const value = String(path || "").trim().replace(/\\/g, "/");
  if (!value || value === "/") return "";
  return value.replace(/^\/+|\/+$/g, "");
}

function displayFolder(path) {
  return path ? path : "/";
}

function collectFolderPaths(app) {
  const files = app?.vault?.getAllLoadedFiles?.() || [];
  const folders = new Set([""]);
  for (const file of files) {
    if (!file || typeof file.path !== "string") continue;
    if (typeof file.children === "undefined") continue;
    folders.add(normalizeFolderPath(file.path));
  }
  return Array.from(folders.values()).sort((a, b) =>
    displayFolder(a).localeCompare(displayFolder(b)),
  );
}

function collectRowsForFolder(folderPath) {
  const normalized = normalizeFolderPath(folderPath);
  const prefix = normalized ? `${normalized}/` : "";

  const files = app.vault
    .getMarkdownFiles()
    .filter((file) => {
      const path = String(file.path || "");
      if (!normalized) return true;
      return path === normalized || path.startsWith(prefix);
    })
    .map((file) => {
      const page = dv.page(file.path);
      return {
        path: file.path,
        title: String(page?.title || file.basename || file.name || file.path),
      };
    })
    .sort((a, b) => a.title.localeCompare(b.title));

  return files;
}

function toAbsolutePaths(relativePaths, app) {
  const adapter = app?.vault?.adapter;
  const basePath =
    (adapter &&
      typeof adapter.getBasePath === "function" &&
      adapter.getBasePath()) ||
    (adapter && adapter.basePath) ||
    "";
  if (!basePath) return [];

  const path = require("path");
  return (relativePaths || [])
    .map((item) => String(item || "").trim())
    .filter(Boolean)
    .map((item) => path.resolve(basePath, item));
}
```
