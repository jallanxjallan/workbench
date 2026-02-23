
```dataviewjs
const SCENES_ROOT = "_project";            // folder containing your scene notes
const ENTRY_INDEX = "_project/content_index.md";  // the single index to inspect

// ---------- helpers ----------
async function loadText(path) { return await dv.io.load(path); }

function extractWikilinks(text) {
  const out = [];
  const re = /\!?(\[\[)([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]/g;
  let m; while ((m = re.exec(text)) !== null) out.push(m[2].trim());
  return out;
}

function resolvePage(target, fromPath) {
  const p = dv.page(target);
  if (p?.file?.path) return p;
  if (fromPath) {
    const baseDir = fromPath.split("/").slice(0, -1).join("/");
    const candidate = baseDir ? `${baseDir}/${target}` : target;
    const p2 = dv.page(candidate);
    if (p2?.file?.path) return p2;
  }
  return null;
}

const isScenePath = p => typeof p === "string" && p.startsWith(SCENES_ROOT + "/");

// ---------- main ----------
(async () => {
  const indexPage = dv.page(ENTRY_INDEX);
  if (!indexPage) {
    dv.paragraph(`❌ Index not found: **${ENTRY_INDEX}**`);
    return;
  }

  // Ground truth: every scene file in the vault
  const allScenes = dv.pages(`"${SCENES_ROOT}"`).array().map(p => p.file.path);
  const allScenesSet = new Set(allScenes);

  const indexText = await loadText(indexPage.file.path);
  const rawTargets = extractWikilinks(indexText);

  // Resolve links and gather counts
  const sceneCounts = new Map();  // scenePath -> count in this index
  const missing = [];             // { targetRaw }
  for (const raw of rawTargets) {
    const resolved = resolvePage(raw, indexPage.file.path);
    if (!resolved) {
      missing.push({ targetRaw: raw });
      continue;
    }
    const rp = resolved.file.path;
    if (isScenePath(rp)) {
      sceneCounts.set(rp, (sceneCounts.get(rp) ?? 0) + 1);
    }
  }

  // Compute sets
const linkedScenes = new Set(sceneCounts.keys());

const unlinkedScenes = [...allScenesSet]
  .filter(s => !linkedScenes.has(s)) // not linked
  .filter(s => {
    const page = dv.page(s);
    const status = (page?.status ?? "").toString().trim();
    return status !== "❌";           // exclude scenes marked not in use
  });

const duplicates = [...sceneCounts.entries()]
  .filter(([, n]) => n > 1)
  .map(([scenePath, count]) => ({ scenePath, count }))
  .sort((a, b) => b.count - a.count || a.scenePath.localeCompare(b.scenePath));


  // Summary
  dv.header(2, "🔎 Single-Index Link Health (content_index.md)");
  dv.paragraph([
    `**Scenes in vault:** ${allScenesSet.size}`,
    `**Linked by this index:** ${linkedScenes.size}`,
    `**Unlinked (not in this index):** ${unlinkedScenes.length}`,
    `**Duplicates (same scene linked >1×):** ${duplicates.length}`,
    `**Missing targets in index:** ${missing.length}`
  ].join(" • "));

  // Duplicates
  dv.header(3, "🔁 Scenes linked more than once");
  if (duplicates.length) {
    dv.table(["Scene", "Count"], duplicates.map(d => [dv.fileLink(d.scenePath), d.count]));
  } else {
    dv.paragraph("✅ No duplicates.");
  }

  // Unlinked scenes
  dv.header(3, "🧭 Scenes not referenced by this index");
  if (unlinkedScenes.length) {
    dv.table(["Scene"], unlinkedScenes.map(p => [dv.fileLink(p)]));
  } else {
    dv.paragraph("✅ All scenes are referenced by this index.");
  }

  // Missing targets
  dv.header(3, "❌ Links in index that don’t resolve");
  if (missing.length) {
    dv.table(["Raw link text"], missing.map(m => [m.targetRaw]));
  } else {
    dv.paragraph("✅ No missing targets.");
  }
})();
```

