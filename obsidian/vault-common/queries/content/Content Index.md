```dataviewjs
(async () => {
  const STORAGE_KEY = "contentIndexFilters_v2";
  const FIELDS = [
    { key: "class", label: "Class" },
    { key: "stage", label: "Stage" },
    { key: "state", label: "State" },
  ];

  // Optional frontmatter: index_note: "Table of Contents.md"
  const INDEX_NOTE = String(dv.current().index_note ?? "Table of Contents.md").trim();

  const container = dv?.container ?? this?.container;
  if (!container) return;
  container.empty();

  const sourceFile = resolveIndexFile(INDEX_NOTE, dv.current().file.path, container);
  if (!sourceFile) {
    return;
  }

  const sourceText = await app.vault.cachedRead(sourceFile);

  const groups = [];
  const headingRe = /^\s{0,3}#{1,6}\s+(.+?)\s*$/;
  const wikilinkRe = /\[\[([^[\]]+?)\]\]/g;
  let currentGroup = null;

  for (const line of sourceText.split(/\r?\n/)) {
    const headingMatch = line.match(headingRe);
    if (headingMatch) {
      currentGroup = { heading: headingMatch[1], rows: [] };
      groups.push(currentGroup);
      continue;
    }

    let m;
    while ((m = wikilinkRe.exec(line)) !== null) {
      if (!currentGroup) {
        currentGroup = { heading: "(No Heading)", rows: [] };
        groups.push(currentGroup);
      }
      currentGroup.rows.push(m[1].trim());
    }
  }

  const usedGroups = groups.filter((g) => g.rows.length > 0);
  if (usedGroups.length === 0) {
    container.createDiv({ text: `No wikilinks found in "${sourceFile.path}".` });
    return;
  }

  const indexedGroups = usedGroups.map((group) => ({
    heading: group.heading,
    rows: group.rows.map((rawLink) => buildIndexRow(rawLink, sourceFile.path)),
  }));
  const allRows = indexedGroups.flatMap((group) => group.rows);
  const values = Object.fromEntries(
    FIELDS.map(({ key }) => [key, collectUniqueValues(allRows, key)]),
  );
  const selected = loadSelected(values);

  // ==============================
  // SHARED COMMAND HANDLERS
  // ==============================
  function getCheckedFileLinks() {
    const checked = [];
    container.querySelectorAll("li[data-file-path]").forEach((row) => {
      const checkbox = row.querySelector("input[type='checkbox']");
      const path = String(row.getAttribute("data-file-path") || "").trim();
      if (checkbox?.checked && path) checked.push(path);
    });
    return checked;
  }

  async function handleProcess() {
    const files = getCheckedFileLinks();
    if (!files.length) {
      if (typeof Notice === "function") new Notice("No files selected.");
      return;
    }

    console.log("Process:", files);
    if (typeof Notice === "function") new Notice("Process not yet implemented.");
  }

  async function handleSubmit() {
    const files = getCheckedFileLinks();
    if (!files.length) {
      if (typeof Notice === "function") new Notice("No files selected.");
      return;
    }

    console.log("Submit stub:", files);
    if (typeof Notice === "function") new Notice("Submit not yet implemented.");
  }

  render();

  function render() {
    container.empty();

    const title = container.createEl("h2", { text: "Content Index" });
    Object.assign(title.style, { margin: "0 0 0.5rem 0" });

    const sourceInfo = container.createDiv();
    Object.assign(sourceInfo.style, { marginBottom: "0.5rem" });
    sourceInfo.append(
      "Index note: ",
      dv.fileLink(sourceFile.path),
    );

    renderFilterHeader({
      parent: container,
      fields: FIELDS,
      values,
      selected,
      onChange: () => {
        saveSelected(selected);
        render();
      },
    });

    container.createEl("hr");

    const summary = container.createDiv();
    Object.assign(summary.style, { marginBottom: "0.5rem" });

    const selectedInAllFields = FIELDS.every(
      ({ key }) => (selected[key]?.size ?? 0) > 0,
    );
    if (!selectedInAllFields) {
      summary.setText("Select one or more values in Class, Stage, and State.");
      renderFooter(container);
      return;
    }

    let renderedCount = 0;
    for (const group of indexedGroups) {
      const matches = group.rows.filter((row) =>
        FIELDS.every(({ key }) => valueMatchesSelection(row[key], selected[key])),
      );
      if (matches.length === 0) continue;

      renderedCount += matches.length;
      container.createEl("h3", { text: group.heading });

      const list = container.createEl("ul");
      Object.assign(list.style, {
        listStyle: "none",
        padding: "0",
        margin: "0.35rem 0 1rem 0",
      });

      for (const rowData of matches) {
        const row = list.createEl("li");
        row.setAttribute("data-file-path", rowData.filePath || "");
        Object.assign(row.style, {
          display: "flex",
          alignItems: "center",
          gap: "0.3rem",
          marginBottom: "0.3rem",
        });

        row.createEl("input", { type: "checkbox" });

        const a = row.createEl("a", {
          text: rowData.linkText,
          href: rowData.href,
          cls: "internal-link",
        });
        a.setAttr("data-href", rowData.href);
      }
    }

    if (renderedCount === 0) {
      summary.setText("No index links match the current Class/Stage/State filter selection.");
      renderFooter(container);
      return;
    }

    summary.setText(
      `Showing ${renderedCount} of ${allRows.length} indexed link${allRows.length === 1 ? "" : "s"}.`,
    );

    renderFooter(container);
  }

  function buildIndexRow(rawLink, fromPath) {
    const [targetPart, aliasPart] = rawLink.split("|");
    const target = String(targetPart ?? "").trim();
    const alias = String(aliasPart ?? "").trim();
    const pageKey = target.split("#")[0].split("^")[0].replace(/\.md$/i, "");

    let page = pageKey ? dv.page(pageKey) : null;
    const resolved = pageKey
      ? app.metadataCache.getFirstLinkpathDest(pageKey, fromPath)
      : null;
    if (!page && resolved?.path) {
      page = dv.page(resolved.path);
    }

    const stageValues = toValueList(page?.stage);
    const stateValues = toValueList(page?.state);
    const classValues = toValueList(page?.class);

    return {
      href: target || rawLink,
      linkText: alias || page?.title || page?.file?.name || target || rawLink,
      filePath: page?.file?.path || resolved?.path || ensureMarkdownPath(pageKey),
      class: classValues,
      stage: stageValues,
      state: stateValues,
    };
  }

  function resolveIndexFile(indexNote, fromPath, container) {
    const base = normalizePath(indexNote);
    const baseNoExt = stripExt(base);
    const baseNameNoExt = stripExt(baseNoExt.split("/").pop() ?? "");

    let sourceFile = null;

    const pathCandidates = base.endsWith(".md") ? [base] : [`${base}.md`, base];
    for (const candidate of pathCandidates) {
      const file = app.vault.getFileByPath(candidate);
      if (file) {
        sourceFile = file;
        break;
      }
    }

    if (!sourceFile) {
      const linkCandidates = [baseNoExt, baseNameNoExt].filter(Boolean);
      for (const candidate of linkCandidates) {
        const file = app.metadataCache.getFirstLinkpathDest(candidate, fromPath);
        if (file) {
          sourceFile = file;
          break;
        }
      }
    }

    if (!sourceFile && baseNameNoExt) {
      const matches = app.vault
        .getMarkdownFiles()
        .filter(
          (file) =>
            String(file.basename ?? "").toLowerCase() === baseNameNoExt.toLowerCase(),
        );
      if (matches.length === 1) {
        sourceFile = matches[0];
      } else if (matches.length > 1) {
        container.createDiv({
          text: `Multiple files named "${baseNameNoExt}.md" found. Set frontmatter index_note to an exact vault path.`,
        });
        const hintList = container.createEl("ul");
        for (const file of matches.slice(0, 10)) {
          hintList.createEl("li", { text: file.path });
        }
        return null;
      }
    }

    if (!sourceFile) {
      container.createDiv({
        text: `Could not load index note "${indexNote}". Try frontmatter index_note: "Table of Contents.md"`,
      });
      return null;
    }

    return sourceFile;
  }

  function renderFilterHeader({ parent, fields, values, selected, onChange }) {
    for (const { key, label } of fields) {
      const row = parent.createDiv();
      Object.assign(row.style, {
        display: "flex",
        alignItems: "center",
        flexWrap: "wrap",
        gap: "0.4rem",
        marginBottom: "0.35rem",
      });

      row.createEl("strong", { text: `${label}:` });

      const selectAll = row.createEl("button", { text: "Select All" });
      selectAll.type = "button";
      selectAll.addEventListener("click", () => {
        selected[key] = new Set(values[key]);
        onChange();
      });

      const clear = row.createEl("button", { text: "Clear" });
      clear.type = "button";
      clear.addEventListener("click", () => {
        selected[key] = new Set();
        onChange();
      });

      if ((values[key]?.length ?? 0) === 0) {
        row.createSpan({ text: "(none)" });
        continue;
      }

      values[key].forEach((value, index) => {
        const token = row.createEl("button", { text: value });
        token.type = "button";
        Object.assign(token.style, {
          cursor: "pointer",
          fontWeight: selected[key].has(value) ? "700" : "400",
          textDecoration: selected[key].has(value) ? "underline" : "none",
          padding: "0.05rem 0.35rem",
        });
        token.addEventListener("click", () => {
          if (selected[key].has(value)) selected[key].delete(value);
          else selected[key].add(value);
          onChange();
        });

        if (index < values[key].length - 1) {
          row.createSpan({ text: "|" });
        }
      });
    }
  }

  function renderFooter(parent) {
    parent.createEl("hr");

    const buttonRow = parent.createDiv();
    Object.assign(buttonRow.style, {
      display: "flex",
      gap: "0.4rem",
      marginTop: "0.5rem",
    });

    const processBtn = buttonRow.createEl("button", { text: "Process" });
    processBtn.type = "button";
    styleCommandButton(processBtn);
    processBtn.addEventListener("click", handleProcess);

    const submitBtn = buttonRow.createEl("button", { text: "Submit" });
    submitBtn.type = "button";
    styleCommandButton(submitBtn);
    submitBtn.addEventListener("click", handleSubmit);
  }

  function styleCommandButton(button) {
    Object.assign(button.style, {
      cursor: "pointer",
      padding: "0.05rem 0.35rem",
    });
  }

  function loadSelected(valuesByField) {
    let parsed = null;
    try {
      parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    } catch {
      parsed = null;
    }

    const out = {};
    for (const { key } of FIELDS) {
      const stored = Array.isArray(parsed?.[key]) ? parsed[key] : valuesByField[key];
      const set = new Set(stored.map(normalizeValue).filter(Boolean));
      for (const value of valuesByField[key]) set.add(value);
      out[key] = set;
    }
    return out;
  }

  function saveSelected(selectedByField) {
    const serializable = {};
    for (const { key } of FIELDS) {
      serializable[key] = [...selectedByField[key]];
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(serializable));
  }

  function collectUniqueValues(sourceRows, field) {
    const set = new Set();
    for (const row of sourceRows) {
      for (const value of row[field] ?? []) set.add(value);
    }
    return [...set].sort((a, b) => a.localeCompare(b));
  }

  function valueMatchesSelection(rowValues, selectedSet) {
    if (!selectedSet || selectedSet.size === 0) return false;
    if (!Array.isArray(rowValues) || rowValues.length === 0) return false;
    return rowValues.some((value) => selectedSet.has(value));
  }

  function toValueList(value) {
    if (Array.isArray(value)) return value.map(normalizeValue).filter(Boolean);
    const single = normalizeValue(value);
    return single ? [single] : [];
  }

  function normalizeValue(value) {
    if (value == null) return "";
    return String(value).trim();
  }

  function normalizePath(value) {
    return String(value ?? "").trim().replace(/\\/g, "/").replace(/^\/+/, "");
  }

  function stripExt(value) {
    return String(value ?? "").replace(/\.md$/i, "");
  }

  function ensureMarkdownPath(pathLike) {
    const clean = String(pathLike ?? "").trim();
    if (!clean) return "";
    return /\.md$/i.test(clean) ? clean : `${clean}.md`;
  }
})();
```
