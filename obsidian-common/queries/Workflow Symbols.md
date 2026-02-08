```dataviewjs
(() => {
  // --- Data (from your "Workflow Symbols") ---
  const categories = {
    compose: [
      { symbol: "💡", desc: "Idea" },
      { symbol: "✍️", desc: "Draft" },
      { symbol: "📝", desc: "Prompt" },
    ],
    process: [
      { symbol: "⚑", desc: "Queue for processing" },
      { symbol: "🤖", desc: "AI Generated" },
      { symbol: "🕵️", desc: "Human Reviewed" },
      { symbol: "📥", desc: "Imported" },
      { symbol: "⚙️", desc: "In Process" },
    ],
    edit: [
      { symbol: "🛑", desc: "Needs Attention" },
      { symbol: "🛠️", desc: "In revision" },
      { symbol: "🔍", desc: "Needs Final Review" },
      { symbol: "✅", desc: "Final Draft" },
      { symbol: "❌", desc: "Omit" },
    ],
    layout: [
      { symbol: "¶", desc: "Running text" },
      { symbol: "🖼️", desc: "Photo caption" },
      { symbol: "⧉", desc: "Boxout" },
      { symbol: "▌", desc: "Sidebar" },
      { symbol: "❝ ❞", desc: "Pull quote" },
      { symbol: "⬖⬘", desc: "Two-page spread" },
      { symbol: "🖼️⛶", desc: "Full-bleed image" },
      { symbol: "✦", desc: "Section opener" },
      { symbol: "⬇", desc: "Page break" },
      { symbol: "∎", desc: "End of chapter" },
    ],
    origin: [
      { symbol: "📝", desc: "Inline note" },
      { symbol: "📷", desc: "Image reference" },
      { symbol: "🔖", desc: "Bookmark/tag" },
      { symbol: "…",  desc: "(ellipsis indicates more codes in source)" },
      { symbol: "🕵️", desc: "Needs review" },
      { symbol: "❌", desc: "Rejected / Discarded" },
      { symbol: "📘", desc: "Published / Final" },
      { symbol: "📦", desc: "Archived" },
    ],
    topics: [
      { symbol: "📖", desc: "Topic — conceptual anchor" },
      { symbol: "✅", desc: "Hub — MOC / connector topic" },
      { symbol: "📐", desc: "Instruction — system or workflow meta" },
    ],
    sources: [
      { symbol: "🟨", desc: "Draft — raw capture (unprocessed material)" },
      { symbol: "📝", desc: "Noted — summarized / skimmed" },
      { symbol: "🔍", desc: "Reviewed — checked for accuracy" },
      { symbol: "📌", desc: "Cited — used in draft text" },
      { symbol: "🏛️", desc: "Authoritative — definitive, in authority table" },
      { symbol: "🗑️", desc: "Discarded — irrelevant" },
    ],
  };

  // --- UI containers ---
  const el = this.container;
  el.empty();

  const controls = el.createDiv();
  Object.assign(controls.style, {
    display: "flex",
    gap: "0.5rem",
    alignItems: "center",
    flexWrap: "wrap",
    marginBottom: "0.75rem",
  });

  controls.createSpan({ text: "Category:" });
  const select = controls.createEl("select");
  Object.keys(categories).forEach((k) => {
    select.createEl("option", { value: k, text: k });
  });

  const search = controls.createEl("input", {
    type: "search",
    placeholder: "Filter…",
  });
  Object.assign(search.style, { marginLeft: "0.5rem" });

  const grid = el.createDiv();
  Object.assign(grid.style, {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
    gap: "0.75rem",
  });

  // --- Render ---
  async function copyToClipboard(text, btn) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Fallback for older setups
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
    btn.textContent = "Copied!";
    setTimeout(() => (btn.textContent = "Copy"), 900);
  }

  function render() {
    const key = select.value;
    const q = (search.value || "").toLowerCase().trim();
    grid.empty();

    (categories[key] || []).forEach((item) => {
      const hay = (item.symbol + " " + item.desc).toLowerCase();
      if (q && !hay.includes(q)) return;

      const card = grid.createDiv();
      Object.assign(card.style, {
        border: "1px solid var(--hr)",
        borderRadius: "12px",
        padding: "0.75rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "0.6rem",
      });

      const left = card.createDiv();
      Object.assign(left.style, { display: "flex", alignItems: "center", gap: "0.6rem" });

      const sym = left.createDiv({ text: item.symbol });
      Object.assign(sym.style, { fontSize: "1.5rem", lineHeight: "1" });

      const desc = left.createDiv({ text: item.desc });
      Object.assign(desc.style, { opacity: "0.9" });

      const btnWrap = card.createDiv();
      const copySymbolBtn = btnWrap.createEl("button", { text: "Copy" });
      Object.assign(copySymbolBtn.style, {
        padding: "0.35rem 0.6rem",
        borderRadius: "8px",
        cursor: "pointer",
      });
      copySymbolBtn.addEventListener("click", () => copyToClipboard(item.symbol, copySymbolBtn));
    });
  }

  select.addEventListener("change", render);
  search.addEventListener("input", render);

  // Init
  select.value = "compose";
  render();
})();

```