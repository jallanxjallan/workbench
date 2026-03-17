// DataviewJS — Content Status (persistent row selection)
// Drop-in replacement for your current Content Status query.
// Adds:
// - persistent checked rows across filter changes
// - selection count
// - Clear Selection button
// - Process/Submit operate on the persistent selection set (not just visible rows)

dataviewjs
(() => {
  const STORAGE_KEY = "contentStatusFilters_v2";
  const CHECKED_KEY = "contentStatusChecked_v1";

  const FIELDS = [
    { key: "class", label: "Class" },
    { key: "stage", label: "Stage" },
    { key: "state", label: "State" },
  ];

  const container = dv?.container ?? this?.container;
  if (!container) {
    if (typeof Notice === "function") new Notice("Content Status: no render container found.");
    return;
  }

  // ==============================
  // DATA
  // ==============================
  const rows = app.vault
    .getMarkdownFiles()
    .filter((file) => String(file.path || "").startsWith("content/"))
    .map((file) => {
      const page = dv.page(file.path) || {};
      return {
        path: file.path,
        title: String(page.title || file.basename || file.name || file.path),
        class: toValueList(page.class),
        stage: toValueList(page.stage),
        state: toValueList(page.state),
      };
    })
    .sort((a, b) => a.title.localeCompare(b.title));

  if (rows.length === 0) {
    container.empty();
    container.createDiv({ text: "No markdown files found in content/." });
    return;
  }

  const values = Object.fromEntries(
    FIELDS.map(({ key }) => [key, collectUniqueValues(rows, key)]),
  );

  const selected = loadSelected(values);
  const checkedSet = loadChecked();

  // Keep selection set tidy: if a file no longer exists, drop it.
  {
    const existing = new Set(rows.map((r) => r.path));
    let changed = false;
    for (const p of [...checkedSet]) {
      if (!existing.has(p)) {
        checkedSet.delete(p);
        changed = true;
      }
    }
    if (changed) saveChecked(checkedSet);
  }

  // ==============================
  // COMMAND HANDLERS
  // ==============================
  function getCheckedFileLinks() {
    return [...checkedSet];
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

  // ==============================
  // RENDER
  // ==============================
  function render() {
    container.empty();

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

    const selectedInAllFields = FIELDS.every(({ key }) => (selected[key]?.size ?? 0) > 0);

    // Compute current matches.
    const matches = selectedInAllFields
      ? rows.filter((row) => FIELDS.every(({ key }) => valueMatchesSelection(row[key], selected[key])))
      : [];

    // Count selected (global) and selected that are currently visible.
    const visiblePaths = new Set(matches.map((m) => m.path));
    const selectedTotal = checkedSet.size;
    let selectedVisible = 0;
    for (const p of checkedSet) if (visiblePaths.has(p)) selectedVisible++;

    if (!selectedInAllFields) {
      summary.setText(
        `Select one or more values in Class, Stage, and State. ` +
          `(Selected: ${selectedTotal} total)`
      );
      renderFooter(container, { selectedTotal, selectedVisible, visibleCount: 0 });
      return;
    }

    summary.setText(
      `${matches.length} file${matches.length === 1 ? "" : "s"} in content/ matching intersection. ` +
        `(Selected: ${selectedTotal} total, ${selectedVisible} visible)`
    );

    if (matches.length === 0) {
      renderFooter(container, { selectedTotal, selectedVisible, visibleCount: 0 });
      return;
    }

    const list = container.createEl("ul");
    Object.assign(list.style, {
      listStyle: "none",
      margin: "0",
      padding: "0",
    });

    for (const row of matches) {
      const item = list.createEl("li");
      item.setAttribute("data-file-path", row.path);
      Object.assign(item.style, {
        display: "flex",
        alignItems: "center",
        gap: "0.3rem",
        marginBottom: "0.3rem",
      });

      const checkbox = item.createEl("input", { type: "checkbox" });
      if (checkedSet.has(row.path)) checkbox.checked = true;

      checkbox.addEventListener("change", () => {
        if (checkbox.checked) checkedSet.add(row.path);
        else checkedSet.delete(row.path);
        saveChecked(checkedSet);

        // Update the summary line without a full rerender.
        // (Rerendering would be fine too, but this keeps the UI snappy.)
        const selectedTotalNow = checkedSet.size;
        let selectedVisibleNow = 0;
        for (const p of checkedSet) if (visiblePaths.has(p)) selectedVisibleNow++;
        summary.setText(
          `${matches.length} file${matches.length === 1 ? "" : "s"} in content/ matching intersection. ` +
            `(Selected: ${selectedTotalNow} total, ${selectedVisibleNow} visible)`
        );
      });

      const target = String(row.path || "").replace(/\.md$/i, "");
      const link = item.createEl("a", {
        text: row.title,
        href: target,
        cls: "internal-link",
      });
      link.setAttr("data-href", target);
    }

    renderFooter(container, {
      selectedTotal,
      selectedVisible,
      visibleCount: matches.length,
    });
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

  function renderFooter(parent, { selectedTotal, selectedVisible, visibleCount }) {
    parent.createEl("hr");

    const footerRow = parent.createDiv();
    Object.assign(footerRow.style, {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      gap: "0.75rem",
      marginTop: "0.5rem",
      flexWrap: "wrap",
    });

    const left = footerRow.createDiv();
    Object.assign(left.style, { display: "flex", gap: "0.4rem", alignItems: "center" });

    const right = footerRow.createDiv();
    Object.assign(right.style, { display: "flex", gap: "0.4rem", alignItems: "center" });

    const meta = left.createSpan({
      text: `Selected: ${selectedTotal} total${visibleCount ? `, ${selectedVisible} visible` : ""}`,
    });
    Object.assign(meta.style, { opacity: "0.8" });

    const clearSelBtn = left.createEl("button", { text: "Clear Selection" });
    clearSelBtn.type = "button";
    styleCommandButton(clearSelBtn);
    clearSelBtn.addEventListener("click", () => {
      checkedSet.clear();
      saveChecked(checkedSet);
      render();
      if (typeof Notice === "function") new Notice("Selection cleared.");
    });

    const processBtn = right.createEl("button", { text: "Process" });
    processBtn.type = "button";
    styleCommandButton(processBtn);
    processBtn.addEventListener("click", handleProcess);

    const submitBtn = right.createEl("button", { text: "Submit" });
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

  // ==============================
  // STATE: FILTER SELECTIONS
  // ==============================
  function loadSelected(valuesByField) {
    let parsed = null;
    try {
      parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    } catch {
      parsed = null;
    }

    const out = {};
    for (const { key } of FIELDS) {
      const stored = Array.isArray(parsed?.[key]) ? parsed[key] : [];
      out[key] = new Set(stored.map(normalizeValue).filter(Boolean));

      // Important: DO NOT auto-select everything by default.
      // If nothing is stored, the user sees the "Select one or more" prompt.
      // (This matches the current UX.)
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

  // ==============================
  // STATE: CHECKED ROWS
  // ==============================
  function loadChecked() {
    try {
      const parsed = JSON.parse(localStorage.getItem(CHECKED_KEY) || "[]");
      return new Set((Array.isArray(parsed) ? parsed : []).map(String));
    } catch {
      return new Set();
    }
  }

  function saveChecked(set) {
    localStorage.setItem(CHECKED_KEY, JSON.stringify([...set]));
  }

  // ==============================
  // HELPERS
  // ==============================
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
})();
