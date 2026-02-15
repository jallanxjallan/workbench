// File: _system/scripts/tp_batch_insert_via_templater_merge_safe.js
// Type: QuickAdd Macro-friendly Templater User Script
// Goal: Let Templater handle YAML merge; use Obsidian's front‑matter API to set status
// and metadataCache positions to insert rendered body (no manual YAML parsing).

/* Usage (QuickAdd Macro → Run Templater user script)
<%* await tp.user.tp_batch_insert_via_templater_merge_safe() %>
// You'll be prompted for: folder, status symbol to match, draft symbol, template, recurse
*/

module.exports = async function () {
  const app = this.app;
  const vault = app.vault;
  const mdCache = app.metadataCache;
  const templater = app.plugins.plugins["templater-obsidian"]; // latest
  const qa = app.plugins.plugins["quickadd"];                 // latest
  if (!templater || !templater.templater) { new Notice("Templater not available"); return; }
  if (!qa || !qa.api) { new Notice("QuickAdd API not available"); return; }
  const tApi = templater.templater;
  const q = qa.api;

  // --- prompts ---
  const folder = await promptFolder(q, vault, "Pick target folder"); if (!folder) return;
  const status_symbol = await q.inputPrompt("Status symbol to match (YAML 'status: …')", "📥"); if (status_symbol == null) return;
  const draft_symbol  = await q.inputPrompt("Draft symbol to set after processing", "📝"); if (draft_symbol == null) return;
  const { templateFile, templatePath } = await promptTemplate(q, vault, templater, "Pick template"); if (!templateFile) return;
  const recurse = await q.yesNoPrompt("Recurse into subfolders?", false);

  // --- collect targets ---
  const files = []; walk(folder, f => { if (f.extension === "md") files.push(f); }, recurse);
  const targets = files.filter(f => {
    const fm = (mdCache.getFileCache(f) || {}).frontmatter || {};
    return String(fm.status) === String(status_symbol);
  });

  let ok = 0;
  for (const file of targets) {
    try {
      // 1) Render template in context of target, let Templater merge FM
      const raw = await vault.read(templateFile);
      const rendered = await tApi.render_template(raw, file);
      await tApi.write_to_file(file, rendered, { merge_frontmatter: true });

      // 2) Prepend rendered BODY (not FM) just after existing FM boundary using metadataCache positions
      const renderedBody = extractBody(rendered);
      if (renderedBody.trim().length) {
        const current = await vault.read(file);
        const pos = (mdCache.getFileCache(file) || {}).frontmatter?.position;
        const insertAt = pos ? pos.end.offset : 0; // just after closing '---' line
        const before = current.slice(0, insertAt);
        const after  = current.slice(insertAt);
        const needsGap = !after.startsWith("\n\n") ? "\n\n" : ""; // avoid piling up newlines
        await vault.modify(file, before + needsGap + renderedBody + (renderedBody.endsWith("\n") ? "" : "\n") + after);
      }

      // 3) Set status to draft via Obsidian's front‑matter API (no manual YAML)
      await app.fileManager.processFrontMatter(file, fm => { fm.status = String(draft_symbol); });

      ok++;
    } catch (e) {
      console.error("Apply failed:", file.path, e);
    }
  }

  new Notice(`Applied '${templatePath}' to ${ok} note(s); status → ${String(ok>0?"📝":"")} (per your input)`);

  // ---------- helpers ----------
  function walk(dir, cb, recurse) {
    for (const child of dir.children) {
      if (child instanceof vault.constructor.TFolder) { if (recurse) walk(child, cb, recurse); }
      else if (child instanceof vault.constructor.TFile) { cb(child); }
    }
  }

  async function promptFolder(q, vault, title) {
    const folders = getAllFolders(vault);
    const choice = await q.suggester(folders.map(f => f.path), folders.map(f => f.path), title);
    return folders.find(f => f.path === choice) || null;
  }

  function getAllFolders(vault) {
    const out = []; const root = vault.getRoot();
    (function walk(dir){ out.push(dir); for (const c of dir.children) if (c instanceof vault.constructor.TFolder) walk(c); })(root);
    return out;
  }

  async function promptTemplate(q, vault, templater, title) {
    const tFolder = templater.settings?.templates_folder || "";
    const base = tFolder ? vault.getAbstractFileByPath(tFolder) : null;
    let files = [];
    if (base && base instanceof vault.constructor.TFolder) { files = collectMdFiles(base); }
    else { const alt = vault.getAbstractFileByPath("_system/templates"); if (alt && alt instanceof vault.constructor.TFolder) files = collectMdFiles(alt); }
    if (files.length === 0) { new Notice("No templates found"); return { templateFile: null, templatePath: null }; }
    const labels = files.map(f => f.path);
    const pick = await q.suggester(labels, labels, title);
    const file = pick ? vault.getAbstractFileByPath(pick) : null; return { templateFile: file, templatePath: pick };
  }

  function collectMdFiles(folder) {
    const acc = [];
    (function walk(dir){ for (const c of dir.children) { if (c instanceof vault.constructor.TFolder) walk(c); else if (c.extension === "md") acc.push(c); } })(folder);
    return acc;
  }

  function extractBody(text) {
    if (text.startsWith("---\n")) {
      const end = text.indexOf("\n---\n", 4);
      if (end !== -1) return text.slice(end + 5);
    }
    return text;
  }
};
