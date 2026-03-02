```dataviewjs
(() => {
  const DEFAULT_DISPATCH_MACRO = "Dispatch: Apply Template To Files";

  const container = dv?.container ?? this?.container;
  if (!container) {
    if (typeof Notice === "function") new Notice("Missing Slug: no render container.");
    return;
  }
  container.empty();

  const current = dv.current?.() || {};
  const dispatchMacro = String(
    current.dispatch_macro || DEFAULT_DISPATCH_MACRO,
  ).trim();

  const selectedFiles = new Set();
  let currentRows = [];

  const toolbar = container.createDiv();
  Object.assign(toolbar.style, {
    display: "flex",
    gap: "0.75rem",
    flexWrap: "wrap",
    alignItems: "center",
    marginBottom: "0.5rem",
  });

  const heading = toolbar.createEl("strong", {
    text: "content/ files with missing, empty, or placeholder slug",
  });
  Object.assign(heading.style, { fontSize: "1.05rem" });

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

  const actionBar = container.createDiv();
  Object.assign(actionBar.style, {
    display: "flex",
    gap: "0.75rem",
    flexWrap: "wrap",
    marginTop: "0.75rem",
  });

  const applyTemplateBtn = actionBar.createEl("button", {
    text: "Apply Template To Selected",
  });
  const makeSlugBtn = actionBar.createEl("button", {
    text: "Make Slug For Selected",
  });

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

  applyTemplateBtn.addEventListener("click", applyTemplateToSelected);
  makeSlugBtn.addEventListener("click", makeSlugForSelected);

  renderRows();

  function renderRows() {
    list.empty();
    currentRows = collectMissingSlugRows(app, dv);

    if (currentRows.length === 0) {
      statusLine.setText(
        "No files in content/ are missing slug, empty slug, or placeholder slug.",
      );
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

      const tag = row.createEl("small", {
        text:
          rowData.slugState === "empty"
            ? "[empty slug]"
            : rowData.slugState === "placeholder"
              ? "[placeholder slug]"
              : "[missing slug]",
      });
      Object.assign(tag.style, { opacity: "0.75" });
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
        new Notice("QuickAdd API not available for template dispatch.");
      }
      return;
    }

    globalThis.__wkbTemplateFilepaths = filepaths;
    try {
      await quickAddApi.executeChoice(dispatchMacro, { filepaths });
      if (typeof Notice === "function") {
        new Notice(`Applied template dispatch to ${filepaths.length} file(s).`);
      }
      renderRows();
    } catch (error) {
      const message = error?.message || String(error);
      if (typeof Notice === "function") {
        new Notice(`Apply template failed: ${message}`);
      }
      console.error(error);
    }
  }

  async function makeSlugForSelected() {
    const selectedRelativePaths = Array.from(selectedFiles.values());
    if (selectedRelativePaths.length === 0) {
      if (typeof Notice === "function") new Notice("No files selected.");
      return;
    }

    let updated = 0;
    let skipped = 0;
    let failed = 0;

    for (const relPath of selectedRelativePaths) {
      const file = app.vault.getAbstractFileByPath(relPath);
      if (!file || file.extension !== "md") {
        skipped += 1;
        continue;
      }

      try {
        const slug = buildSlugViaCli(app, relPath);
        const text = await app.vault.read(file);
        const out = String(text || "").replace(
          /^(\s*slug:\s*)__SLUG__(\s*)$/m,
          (_, prefix, suffix) => `${prefix}${slug}${suffix}`,
        );

        if (out === text) {
          skipped += 1;
          continue;
        }

        await app.vault.modify(file, out);
        updated += 1;
      } catch (error) {
        failed += 1;
        console.error(error);
      }
    }

    if (typeof Notice === "function") {
      new Notice(
        `make_slug complete. Updated: ${updated}. Skipped: ${skipped}. Failed: ${failed}.`,
        10000,
      );
    }

    renderRows();
  }
})();

function collectMissingSlugRows(app, dv) {
  const rows = [];
  for (const file of app.vault.getMarkdownFiles()) {
    const path = String(file.path || "");
    if (!path.startsWith("content/")) continue;

    const frontmatter = app.metadataCache.getFileCache(file)?.frontmatter || {};
    const hasSlug = Object.prototype.hasOwnProperty.call(frontmatter, "slug");
    const slugValue = frontmatter.slug;
    const slugText = typeof slugValue === "string" ? slugValue.trim() : "";
    const isEmptySlug =
      slugValue == null ||
      (typeof slugValue === "string" && slugText === "");
    const isPlaceholderSlug =
      typeof slugValue === "string" &&
      /^__slug__$/i.test(slugText);
    if (!hasSlug) {
      const page = dv.page(path) || {};
      rows.push({
        path,
        title: String(page?.title || file.basename || file.name || path),
        slugState: "missing",
      });
      continue;
    }
    if (hasSlug && !isEmptySlug && !isPlaceholderSlug) continue;

    const page = dv.page(path) || {};
    rows.push({
      path,
      title: String(page?.title || file.basename || file.name || path),
      slugState: isPlaceholderSlug ? "placeholder" : "empty",
    });
  }
  rows.sort((a, b) => a.title.localeCompare(b.title));
  return rows;
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

function buildSlugViaCli(app, relativePath) {
  const { execFileSync } = require("child_process");
  const path = require("path");

  const adapter = app?.vault?.adapter;
  const basePath =
    (adapter &&
      typeof adapter.getBasePath === "function" &&
      adapter.getBasePath()) ||
    (adapter && adapter.basePath) ||
    "";
  if (!basePath) throw new Error("vault base path is unavailable");

  const fullPath = path.resolve(basePath, String(relativePath || ""));
  const folderPath = path.dirname(fullPath);
  const filename = path.basename(fullPath);
  const wkbBin = process.env.WKB_BIN || "wkb";

  const output = execFileSync(wkbBin, ["slug", folderPath, filename], {
    encoding: "utf-8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  const slug = String(output || "").trim();
  if (!slug) throw new Error("empty slug from CLI");
  return slug;
}
```
