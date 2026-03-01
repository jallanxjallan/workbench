```dataviewjs
(() => {
  const FOLDER_PATH = "HHP";
  const DISPATCH_MACRO = "Dispatch: Apply Template To Files";

  const container = dv?.container ?? this?.container;
  if (!container) {
    if (typeof Notice === "function") new Notice("HHP Folder Selector: no render container.");
    return;
  }
  container.empty();

  const pages = dv
    .pages(`"${FOLDER_PATH}"`)
    .where((p) => String(p?.file?.path || "").toLowerCase().endsWith(".md"))
    .sort((p) => p.file.path, "asc");

  if (!pages || pages.length === 0) {
    container.createDiv({ text: `No markdown files found in folder '${FOLDER_PATH}'.` });
    return;
  }

  const filepaths = pages.array().map((p) => String(p.file.path || ""));
  const selected = new Set();

  const toolbar = container.createDiv();
  Object.assign(toolbar.style, {
    display: "flex",
    gap: "0.75rem",
    flexWrap: "wrap",
    marginBottom: "0.75rem",
  });

  const selectAllBtn = toolbar.createEl("button", { text: "Select All" });
  const clearBtn = toolbar.createEl("button", { text: "Clear" });
  const applyBtn = toolbar.createEl("button", { text: "Apply Template" });

  const countLabel = container.createDiv();
  Object.assign(countLabel.style, { marginBottom: "0.5rem" });

  const list = container.createEl("ul");
  Object.assign(list.style, {
    listStyle: "none",
    padding: "0",
    margin: "0 0 0.75rem 0",
  });

  const outputTitle = container.createEl("h4", { text: "Selected absolute paths" });
  const output = container.createEl("pre");
  Object.assign(output.style, {
    whiteSpace: "pre-wrap",
    overflowWrap: "anywhere",
    margin: "0",
  });

  for (const relPath of filepaths) {
    const row = list.createEl("li");
    Object.assign(row.style, {
      display: "flex",
      alignItems: "center",
      gap: "0.5rem",
      marginBottom: "0.35rem",
    });

    const checkbox = row.createEl("input", { type: "checkbox" });
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) selected.add(relPath);
      else selected.delete(relPath);
      renderSelection();
    });

    const target = relPath.replace(/\.md$/i, "");
    const link = row.createEl("a", {
      text: relPath,
      href: target,
      cls: "internal-link",
    });
    link.setAttr("data-href", target);
  }

  selectAllBtn.addEventListener("click", () => {
    selected.clear();
    for (const relPath of filepaths) selected.add(relPath);
    for (const checkbox of list.querySelectorAll("input[type='checkbox']")) {
      checkbox.checked = true;
    }
    renderSelection();
  });

  clearBtn.addEventListener("click", () => {
    selected.clear();
    for (const checkbox of list.querySelectorAll("input[type='checkbox']")) {
      checkbox.checked = false;
    }
    renderSelection();
  });

  applyBtn.addEventListener("click", async () => {
    const absolutePaths = getSelectedAbsolutePaths(selected, app);
    if (absolutePaths.length === 0) {
      if (typeof Notice === "function") new Notice("No files selected.");
      return;
    }

    // Expose as strict absolute paths payload.
    globalThis.__wkbTemplateFilepaths = absolutePaths;

    const qa = app?.plugins?.plugins?.quickadd?.api;
    if (!qa || typeof qa.executeChoice !== "function") {
      if (typeof Notice === "function") new Notice("QuickAdd API not available.");
      return;
    }

    try {
      await qa.executeChoice(DISPATCH_MACRO, { filepaths: absolutePaths });
    } catch (error) {
      const message = error?.message || String(error);
      if (typeof Notice === "function") new Notice(`Dispatch failed: ${message}`);
      console.error(error);
    }
  });

  function renderSelection() {
    const absolutePaths = getSelectedAbsolutePaths(selected, app);
    countLabel.setText(
      `${absolutePaths.length} file${absolutePaths.length === 1 ? "" : "s"} selected.`,
    );
    output.setText(
      JSON.stringify(absolutePaths, null, 2),
    );
  }

  renderSelection();
})();

function getSelectedAbsolutePaths(selectedSet, app) {
  const selected = Array.from(selectedSet.values());
  const path = require("path");
  const adapter = app?.vault?.adapter;
  const basePath =
    (adapter && typeof adapter.getBasePath === "function" && adapter.getBasePath()) ||
    (adapter && adapter.basePath) ||
    "";

  if (!basePath) return [];
  return selected.map((rel) => path.resolve(basePath, rel));
}
```
