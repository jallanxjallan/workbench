```dataviewjs
// === CONFIG ===
const ROOT = "instructions";      // path inside THIS vault (e.g., "External/Instructions")
const COMMON_PREFIX = "common";   // where common is mounted inside THIS vault (optional)
const USE_TOP   = true;
const SEPARATOR = "\n\n---\n\n";

// === Helpers ===
const HRULE = /^\s*---\s*$/m;
const topSegment = t => (t ? (t.split(HRULE)[0] ?? t).trim() : "");
const norm = s => {
  let p = String(s || "").trim();
  if (!p) return "";
  if (!p.toLowerCase().endsWith(".md")) p += ".md";
  return p.replaceAll("\\", "/");
};
const read = async path => {
  const af = app.vault.getAbstractFileByPath(path);
  if (!af) return "";
  try { return await app.vault.cachedRead(af); } catch { return ""; }
};
const part = async path => (USE_TOP ? topSegment(await read(path)) : (await read(path)) || "");
const resolveLocal  = path => app.vault.getAbstractFileByPath(path) ? path : null;
const resolveCommon = path => {
  if (!COMMON_PREFIX) return null;
  const joined = `${COMMON_PREFIX}/${path}`.replaceAll("//", "/");
  return app.vault.getAbstractFileByPath(joined) ? joined : null;
};

// === UI containers ===
const root = dv.container;
const wrap = root.createEl("div", { cls: "inst-wrap" });
const controls = wrap.createEl("div", { cls: "inst-controls" });
controls.createEl("label", { text: "Folder: " });
const sel = controls.createEl("select");
const out = wrap.createEl("div", { cls: "inst-results" });

// styling
const style = document.createElement("style");
style.textContent = `
.inst-controls { display:flex; align-items:center; gap:.5rem; margin:.25rem 0 .75rem; }
.inst-row { margin:.25rem 0 .5rem; gap:.5rem; display:flex; align-items:center; flex-wrap:wrap; }
.inst-label { font-weight:700; }
.inst-path { color: var(--text-muted); font-size:.9em; }
.inst-copy { padding:.2rem .5rem; }
.inst-block { white-space: pre-wrap; font-family: var(--font-monospace);
  border:1px solid var(--background-modifier-border); padding:.6rem; border-radius:.4rem; }
.inst-warn { color: var(--color-red); margin:.25rem 0; }
`;
document.head.appendChild(style);

function header(container, label, srcPath, assembled) {
  const row = container.createEl("div", { cls: "inst-row" });
  row.createEl("span", { text: label, cls: "inst-label" });
  if (srcPath) row.createEl("span", { text: "  —  " + srcPath, cls: "inst-path" });

  const copyLabelBtn = row.createEl("button", { text: "Copy label", cls: "inst-copy" });
  copyLabelBtn.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(label); new Notice(`Copied label: ${label}`); }
    catch { new Notice("Clipboard write failed"); }
  });

  const copyTextBtn = row.createEl("button", { text: "Copy text", cls: "inst-copy" });
  copyTextBtn.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(assembled); new Notice(`Copied text for: ${label}`); }
    catch { new Notice("Clipboard write failed"); }
  });
}
function block(container, text) {
  const pre = container.createEl("pre", { cls: "inst-block" });
  pre.textContent = text || "";
}

// Discover subfolders by looking at page folder paths.
// (Works as long as there is at least one .md in each subfolder.)
function discoverModes() {
  const pages = dv.pages(`"${ROOT}"`).where(p => p.file && p.file.extension === "md");
  const modes = new Set();
  for (const p of pages) {
    const folder = p.file.folder || "";
    if (!folder.startsWith(`${ROOT}/`)) continue;
    const rel = folder.slice(ROOT.length + 1);
    const head = (rel.split("/")[0] || "").trim();
    if (head) modes.add(head);
  }
  return Array.from(modes).sort();
}

async function render(mode) {
  out.empty();
  const folder = `${ROOT}/${mode}`;
  const pages = dv.pages(`"${folder}"`)
    .where(p => p.file && p.file.extension === "md")
    .sort(p => p.label ?? p.file.name, 'asc');

  if (!pages.length) {
    out.createEl("div", { cls: "inst-warn", text: `No Markdown files in: ${folder}` });
    return;
  }

  for (const p of pages) {
    const label   = p.label ?? p.file.name;
    const context = Array.isArray(p.context) ? p.context : []; // optional
    const roles   = Array.isArray(p.roles)   ? p.roles   : []; // optional

    const parts = [];

    // Local refs (optional)
    for (const ref of context) {
      const path = norm(ref);
      const resolved = resolveLocal(path);
      if (!resolved) { out.createEl("div", { text: `⚠️ Missing local: ${path}`, cls: "inst-warn" }); continue; }
      const seg = await part(resolved);
      if (seg.trim()) parts.push(seg.trim());
    }

    // Common refs (optional)
    for (const ref of roles) {
      const path = norm(ref);
      const resolved = resolveCommon(path);
      if (!resolved) {
        const msg = COMMON_PREFIX ? `${COMMON_PREFIX}/${path}` : path;
        out.createEl("div", { text: `⚠️ Missing common: ${msg}`, cls: "inst-warn" });
        continue;
      }
      const seg = await part(resolved);
      if (seg.trim()) parts.push(seg.trim());
    }

    // Fallback to the instruction note itself
    if (!parts.length) {
      const selfText = await part(p.file.path);
      if (selfText.trim()) parts.push(selfText.trim());
    }

    const assembled = parts.join(SEPARATOR);

    const item = out.createEl("div", { cls: "inst-item" });
    header(item, label, p.file.path, assembled);
    block(item, assembled);
  }
}

// Build the dropdown and kick off
const modes = discoverModes();
if (!modes.length) {
  out.createEl("div", { cls: "inst-warn", text: `No subfolders discovered under: ${ROOT}` });
  out.createEl("div", { text: "Ensure subfolders contain at least one .md file so Dataview can see them." });
} else {
  for (const m of modes) sel.createEl("option", { text: m, value: m });
  sel.value = sel.value || modes[0];
  await render(sel.value);
  sel.addEventListener("change", () => render(sel.value));
}

```