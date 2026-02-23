```dataviewjs
(() => {
  // DataviewJS: select content files by stage value, show newest titles first

  const container = dv?.container ?? this?.container;
  if (!container) {
    if (typeof Notice === "function") new Notice("Draft Status: no render container found.");
    return;
  }
  container.empty();
  const isContent = p => String(p.type ?? "").trim().toLowerCase() === "content";
  const hasStage = p => typeof p.stage !== "undefined" && p.stage !== null;

  // Always-available action
  const actionBar = container.createDiv();
  Object.assign(actionBar.style, {
    display: "flex",
    gap: "0.75rem",
    flexWrap: "wrap",
    marginBottom: "0.5rem"
  });

  const runBatchBtn = actionBar.createEl("button", { text: "Run command" });
  runBatchBtn.setAttr("aria-label", "Run command: Insert Batch Sentinel From Query");
  runBatchBtn.addEventListener("click", async () => {
    const cmdId = resolveBatchSentinelCommandId(app);
    if (!cmdId) {
      new Notice("Command not found: QuickAdd: Insert Batch Sentinel From Query");
      return;
    }
    const ok = await app.commands.executeCommandById(cmdId);
    if (!ok) {
      new Notice("Failed to run Insert Batch Sentinel From Query command.");
    }
  });

  // --- Data ---
  const contentPages = dv.pages().where(isContent);
  if (!contentPages || contentPages.length === 0) {
    container.createDiv({ text: "No files found with type='content'." });
    return;
  }

  const allPages = contentPages.where(hasStage);
  if (!allPages || allPages.length === 0) {
    container.createDiv({ text: "No type='content' files have a 'stage' value yet." });
    return;
  }

  const stageValues = Array.from(new Set(allPages.map(p => String(p.stage)))).sort();

  // --- Controls ---
  const controls = container.createDiv();
  Object.assign(controls.style, {
    display: "flex",
    gap: "0.75rem",
    flexWrap: "wrap",
    marginBottom: "0.5rem"
  });

  const btnWrap = controls.createDiv();
  const selAllBtn = btnWrap.createEl("button", { text: "Select all" });
  const clrAllBtn = btnWrap.createEl("button", { text: "Clear all" });

  const cbWrap = controls.createDiv();
  Object.assign(cbWrap.style, {
    display: "flex",
    gap: "0.75rem",
    flexWrap: "wrap",
    alignItems: "center"
  });

  const state = new Map();
  const cbs = stageValues.map(stageValue => {
    const label = cbWrap.createEl("label");
    Object.assign(label.style, { display: "inline-flex", alignItems: "center", gap: "0.35rem" });

    const cb = label.createEl("input", { type: "checkbox" });
    cb.checked = false;
    label.createSpan({ text: stageValue });

    state.set(stageValue, cb);
    cb.addEventListener("change", render);
    return cb;
  });

  const results = container.createDiv({ cls: "status-results" });
  Object.assign(results.style, { marginTop: "0.75rem" });

  selAllBtn.addEventListener("click", () => {
    cbs.forEach(cb => (cb.checked = true));
    render();
  });

  clrAllBtn.addEventListener("click", () => {
    cbs.forEach(cb => (cb.checked = false));
    render();
  });

  function render() {
    results.empty();

    const selected = stageValues.filter(stageValue => state.get(stageValue)?.checked);
    if (selected.length === 0) {
      results.createDiv({ text: "Select one or more stage values to see matching titles." });
      return;
    }

    const matches = dv
      .pages()
      .where(
        p =>
          isContent(p) &&
          hasStage(p) &&
          selected.includes(String(p.stage))
      )
      .sort(p => p.file.mtime, "desc");

    results.createDiv({
      text: `${matches.length} file${matches.length === 1 ? "" : "s"} matching: ${selected.join(", ")}`
    });

    const list = results.createEl("ul");
    Object.assign(list.style, {
      listStyle: "none",
      padding: "0",
      margin: "0.5rem 0 0 0"
    });

    matches.forEach(p => {
      const item = list.createEl("li");
      Object.assign(item.style, {
        display: "flex",
        alignItems: "center",
        gap: "0.5rem",
        marginBottom: "0.35rem"
      });

      item.createEl("input", { type: "checkbox" });
      const target = String(p.file.path ?? "").replace(/\.md$/i, "");
      const display = p.title ?? p.file.name;
      const link = item.createEl("a", {
        text: display,
        href: target,
        cls: "internal-link"
      });
      link.setAttr("data-href", target);
    });
  }

  render();
})();

function resolveBatchSentinelCommandId(app) {
  const commands = app?.commands?.commands || {};
  const all = Object.values(commands);

  const exact = all.find(c => c?.name === "QuickAdd: Insert Batch Sentinel From Query");
  if (exact?.id) return exact.id;

  const partial = all.find(c => /insert batch sentinel from query/i.test(String(c?.name || "")));
  if (partial?.id) return partial.id;

  return "";
}
```
