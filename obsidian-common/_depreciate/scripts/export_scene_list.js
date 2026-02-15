// export_scene_list.js
// Strict exporter + flat path list + clipboard copy
//
// Usage (Templater):
//   <%* await tp.user.export_scene_list() %>
//   // or with overrides:
//   <%* await tp.user.export_scene_list('"Scenes"', '📝', 'prompt', '/tmp/obsidian_selected_files.json', '/tmp/obsidian_selected_files.txt') %>

module.exports = async (
  tp,
  source = '"Scenes"',                    // Dataview source
  requiredStatus = '📝',                  // frontmatter status
  requiredType = 'prompt',               // frontmatter type
  jsonOut = '/tmp/obsidian_selected_files.json',
  listOut = '/tmp/obsidian_selected_files.txt'
) => {
  const fs = require('fs');

  const dv = app.plugins.plugins["dataview"]?.api;
  if (!dv) throw new Error("Dataview plugin API not available.");

  const ensureMd = p => (p?.endsWith(".md") ? p : `${p}.md`);

  function normalizeToPath(input) {
    if (!input) return null;
    if (Array.isArray(input)) input = input[0];

    // Dataview link object (frontmatter link)
    if (typeof input === "object" && input.path) return ensureMd(input.path);

    if (typeof input !== "string") return null;

    // [[wikilink]] / [[wikilink|alias]] / [[wikilink#heading]]
    const m = input.match(/\[\[([^\]|#]+)(?:#[^\]]*)?(?:\|[^\]]+)?\]\]/);
    if (m) return ensureMd(m[1]);

    // plain path or bare name
    return ensureMd(input);
  }

  function mustExistFile(vaultRelPath, label, scenePath, errs) {
    const f = app.vault.getAbstractFileByPath(vaultRelPath);
    if (!f) { errs.push(`Missing ${label}: "${vaultRelPath}" (referenced by ${scenePath})`); return; }
    if (f.constructor.name !== "TFile") { errs.push(`Not a file for ${label}: "${vaultRelPath}" (referenced by ${scenePath})`); }
  }

  // Query scenes
  const pages = dv.pages(source)
    .where(p => p.status === requiredStatus && p.type === requiredType)
    .sort(p => p.file.path, 'asc');

  const rows = [];
  const errors = [];

  for (const p of pages) {
    const scene_path = ensureMd(p.file.path);

    const smRaw = p.system_message ?? p.systemMessage ?? p.systemmessage ?? null;
    const system_message_path = normalizeToPath(smRaw);
    if (!system_message_path) errors.push(`Scene "${scene_path}" is missing a system_message reference.`);
    else mustExistFile(system_message_path, "system_message", scene_path, errors);

    const rmRaw = p.role_message ?? p.roleMessage ?? p.rolemessage ?? null;
    const role_message_path = normalizeToPath(rmRaw);
    if (!role_message_path) errors.push(`Scene "${scene_path}" is missing a role_message reference.`);
    else mustExistFile(role_message_path, "role_message", scene_path, errors);

    rows.push({ scene_path, system_message_path, role_message_path });
  }

  // Duplicate check on scene_path
  const counts = new Map();
  for (const r of rows) counts.set(r.scene_path, (counts.get(r.scene_path) || 0) + 1);
  const dups = [...counts.entries()].filter(([, n]) => n > 1);
  if (dups.length) {
    for (const [path, n] of dups) errors.push(`Duplicate scene selected ${n}×: "${path}"`);
  }

  // Fail fast with summary if anything wrong
  if (errors.length) {
    throw new Error(`❌ Validation failed (${errors.length} issue${errors.length > 1 ? 's' : ''}):\n- ` + errors.join("\n- "));
  }

  // Write JSON (structured for your API)
  fs.writeFileSync(jsonOut, JSON.stringify(rows, null, 2));

  // Build flat list of unique vault-relative paths (scene + system + role)
  const flatSet = new Set();
  for (const r of rows) {
    flatSet.add(r.scene_path);
    flatSet.add(r.system_message_path);
    flatSet.add(r.role_message_path);
  }
  const flatList = [...flatSet].join("\n");
  fs.writeFileSync(listOut, flatList);

  // Copy the /tmp list file path to clipboard (best-effort)
  const clipText = listOut;
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(clipText);
    } else if (app?.clipboard) {
      // some Obsidian builds expose clipboard on app
      app.clipboard.writeText(clipText);
    } else {
      // Fallback: put also in a notice for quick select
      new Notice(`📋 Copy manually: ${clipText}`, 8000);
    }
  } catch (e) {
    console.error("Clipboard write failed:", e);
    new Notice(`⚠️ Clipboard write failed. Path: ${clipText}`, 8000);
  }

  new Notice(`✅ Exported ${rows.length} scenes →\nJSON: ${jsonOut}\nList: ${listOut}`, 6000);
  return { jsonOut, listOut, count: rows.length };
};
 
