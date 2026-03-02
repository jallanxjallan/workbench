```dataviewjs
(() => {
  const container = dv?.container ?? this?.container;
  if (!container) {
    if (typeof Notice === "function") new Notice("Content Stage: no render container found.");
    return;
  }
  container.empty();
  const rows = app.vault
    .getMarkdownFiles()
    .filter((file) => String(file.path || "").startsWith("content/"))
    .map((file) => {
      const page = dv.page(file.path) || {};
      return {
        path: file.path,
        title: String(page.title || file.basename || file.name || file.path),
        type: normalizeValue(page.type),
        stage: normalizeValue(page.stage),
      };
    })
    .sort((a, b) => a.title.localeCompare(b.title));

  if (rows.length === 0) {
    container.createDiv({ text: "No markdown files found in content/." });
    return;
  }

  const typeValues = uniqueSorted(rows.map((row) => row.type).filter(Boolean));
  const stageValues = uniqueSorted(rows.map((row) => row.stage).filter(Boolean));

  if (typeValues.length === 0) {
    container.createDiv({ text: "No 'type' values found in content/ frontmatter." });
    return;
  }
  if (stageValues.length === 0) {
    container.createDiv({ text: "No 'stage' values found in content/ frontmatter." });
    return;
  }

  const selectedTypes = new Set();
  const selectedStages = new Set();

  const title = container.createEl("h2", { text: "Content Stage" });
  Object.assign(title.style, { margin: "0 0 0.5rem 0" });

  const controls = container.createDiv();
  Object.assign(controls.style, {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
    gap: "0.9rem",
    marginBottom: "0.75rem",
  });

  renderFacetSection({
    parent: controls,
    label: "Type",
    values: typeValues,
    selected: selectedTypes,
    onChange: renderResults,
  });

  renderFacetSection({
    parent: controls,
    label: "Stage",
    values: stageValues,
    selected: selectedStages,
    onChange: renderResults,
  });

  const summary = container.createDiv();
  Object.assign(summary.style, { marginBottom: "0.5rem" });

  const list = container.createEl("ul");
  Object.assign(list.style, {
    listStyle: "none",
    margin: "0",
    padding: "0",
  });

  renderResults();

  function renderResults() {
    list.empty();

    const selectedTypeValues = typeValues.filter((value) => selectedTypes.has(value));
    const selectedStageValues = stageValues.filter((value) => selectedStages.has(value));

    if (selectedTypeValues.length === 0 || selectedStageValues.length === 0) {
      summary.setText("Select one or more values in both Type and Stage.");
      return;
    }

    const matches = rows.filter(
      (row) =>
        selectedTypes.has(row.type) &&
        selectedStages.has(row.stage),
    );

    summary.setText(
      `${matches.length} file${matches.length === 1 ? "" : "s"} in content/ matching intersection.`,
    );

    if (matches.length === 0) return;

    for (const row of matches) {
      const item = list.createEl("li");
      Object.assign(item.style, { marginBottom: "0.3rem" });

      const target = String(row.path || "").replace(/\.md$/i, "");
      const link = item.createEl("a", {
        text: row.title,
        href: target,
        cls: "internal-link",
      });
      link.setAttr("data-href", target);
    }
  }
})();

function renderFacetSection({ parent, label, values, selected, onChange }) {
  const section = parent.createDiv();

  const header = section.createDiv();
  Object.assign(header.style, {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    marginBottom: "0.4rem",
    flexWrap: "wrap",
  });

  header.createEl("strong", { text: label });
  const selectAllBtn = header.createEl("button", { text: "Select all" });
  const clearAllBtn = header.createEl("button", { text: "Clear all" });

  selectAllBtn.addEventListener("click", () => {
    selected.clear();
    for (const value of values) selected.add(value);
    syncCheckboxes(section, selected);
    onChange();
  });

  clearAllBtn.addEventListener("click", () => {
    selected.clear();
    syncCheckboxes(section, selected);
    onChange();
  });

  const options = section.createDiv();
  Object.assign(options.style, {
    display: "flex",
    gap: "0.65rem",
    flexWrap: "wrap",
  });

  for (const value of values) {
    const optionLabel = options.createEl("label");
    Object.assign(optionLabel.style, {
      display: "inline-flex",
      alignItems: "center",
      gap: "0.3rem",
    });

    const checkbox = optionLabel.createEl("input", { type: "checkbox" });
    checkbox.setAttr("data-value", value);
    checkbox.checked = selected.has(value);
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) selected.add(value);
      else selected.delete(value);
      onChange();
    });

    optionLabel.createSpan({ text: value });
  }
}

function syncCheckboxes(section, selected) {
  const inputs = section.querySelectorAll("input[type='checkbox'][data-value]");
  for (const input of inputs) {
    const value = String(input.getAttribute("data-value") || "");
    input.checked = selected.has(value);
  }
}

function normalizeValue(value) {
  if (value == null) return "";
  return String(value).trim();
}

function uniqueSorted(values) {
  return Array.from(new Set(values)).sort((a, b) => a.localeCompare(b));
}
```
