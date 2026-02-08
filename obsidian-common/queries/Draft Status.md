
```dataviewjs
(() => {
  // DataviewJS: filter pages by status; render link + status in a table

  const TARGET_FOLDER = "passages"; // ← change this as needed

  const container = this.container;
  container.empty();

  // --- Data ---
  const allPages = dv.pages(`"${TARGET_FOLDER}"`).where(p => p.status);
  if (!allPages || allPages.length === 0) {
    container.createDiv({ text: `No pages with a 'status' field found in "${TARGET_FOLDER}/".` });
    return;
  }
  const statuses = Array.from(new Set(allPages.map(p => String(p.status)))).sort();

  // --- Controls ---
  const controls = container.createDiv();
  Object.assign(controls.style, { display: "flex", gap: "0.75rem", flexWrap: "wrap", marginBottom: "0.5rem" });

  const btnWrap = controls.createDiv();
  const selAllBtn = btnWrap.createEl("button", { text: "Select all" });
  const clrAllBtn = btnWrap.createEl("button", { text: "Clear all" });

  const cbWrap = controls.createDiv();
  Object.assign(cbWrap.style, { display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "center" });

  const state = new Map();
  const cbs = statuses.map(sym => {
    const label = cbWrap.createEl("label");
    Object.assign(label.style, { display: "inline-flex", alignItems: "center", gap: "0.35rem" });
    const cb = label.createEl("input", { type: "checkbox" });
    cb.checked = false;
    label.createSpan({ text: sym });
    state.set(sym, cb);
    cb.addEventListener("change", render);
    return cb;
  });

  const results = container.createDiv({ cls: "status-results" });
  Object.assign(results.style, { marginTop: "0.75rem" });

  selAllBtn.addEventListener("click", () => { cbs.forEach(cb => cb.checked = true); render(); });
  clrAllBtn.addEventListener("click", () => { cbs.forEach(cb => cb.checked = false); render(); });

  function render() {
    results.empty();

    const selected = statuses.filter(sym => state.get(sym)?.checked);
    if (selected.length === 0) {
      results.createDiv({ text: "Select one or more statuses to see matching pages." });
      return;
    }

    const matches = dv.pages(`"${TARGET_FOLDER}"`)
      .where(p => p.status && selected.includes(String(p.status)))
      .sort(p => p.file.name);

    // Summary
    results.createDiv({
      text: `${matches.length} file${matches.length === 1 ? "" : "s"} matching: ${selected.join(" ")}`
    });

    // Render table (File link + Status) inside `results`
    const prev = dv.container;
    try {
      dv.container = results;
      dv.table(["File", "Status"], matches.map(p => [p.file.link, p.status]).array());
    } finally {
      dv.container = prev;
    }
  }

  // Initial paint
  render();
})();

```
