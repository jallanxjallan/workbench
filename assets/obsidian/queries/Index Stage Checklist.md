```dataviewjs
(async () => {
  // Optional frontmatter: index_note: "Table of Contents.md"
  const INDEX_NOTE = String(dv.current().index_note ?? "Table of Contents.md").trim();

  const container = this.container;
  container.empty();

  const normalizePath = p => String(p ?? "").trim().replace(/\\/g, "/").replace(/^\/+/, "");
  const stripExt = s => String(s ?? "").replace(/\.md$/i, "");
  const base = normalizePath(INDEX_NOTE);
  const baseNoExt = stripExt(base);
  const baseNameNoExt = stripExt(baseNoExt.split("/").pop() ?? "");

  let sourceFile = null;

  // 1) Exact vault-root-relative path lookup
  const pathCandidates = base.endsWith(".md") ? [base] : [`${base}.md`, base];
  for (const c of pathCandidates) {
    const f = app.vault.getFileByPath(c);
    if (f) {
      sourceFile = f;
      break;
    }
  }

  // 2) Obsidian linkpath resolution from current note
  if (!sourceFile) {
    const linkCandidates = [baseNoExt, baseNameNoExt].filter(Boolean);
    for (const c of linkCandidates) {
      const f = app.metadataCache.getFirstLinkpathDest(c, dv.current().file.path);
      if (f) {
        sourceFile = f;
        break;
      }
    }
  }

  // 3) Basename fallback (unique match only)
  if (!sourceFile && baseNameNoExt) {
    const matches = app.vault
      .getMarkdownFiles()
      .filter(f => String(f.basename ?? "").toLowerCase() === baseNameNoExt.toLowerCase());
    if (matches.length === 1) {
      sourceFile = matches[0];
    } else if (matches.length > 1) {
      container.createDiv({
        text: `Multiple files named "${baseNameNoExt}.md" found. Set frontmatter index_note to an exact vault path.`
      });
      const hintList = container.createEl("ul");
      for (const f of matches.slice(0, 10)) {
        hintList.createEl("li", { text: f.path });
      }
      return;
    }
  }

  if (!sourceFile) {
    container.createDiv({
      text: `Could not load index note "${INDEX_NOTE}". Try frontmatter index_note: "Table of Contents.md"`
    });
    return;
  }
  const sourceText = await app.vault.cachedRead(sourceFile);
  const resolvedSource = sourceFile.path;

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

  const usedGroups = groups.filter(g => g.rows.length > 0);
  if (usedGroups.length === 0) {
    container.createDiv({ text: `No wikilinks found in "${resolvedSource}".` });
    return;
  }

  const hasValue = v => typeof v !== "undefined" && v !== null && String(v).trim() !== "";

  for (const group of usedGroups) {
    container.createEl("h3", { text: group.heading });

    const list = container.createEl("ul");
    Object.assign(list.style, {
      listStyle: "none",
      padding: "0",
      margin: "0.35rem 0 1rem 0"
    });

    for (const rawLink of group.rows) {
      const [targetPart, aliasPart] = rawLink.split("|");
      const target = String(targetPart ?? "").trim();
      const alias = String(aliasPart ?? "").trim();
      const pageKey = target.split("#")[0].split("^")[0].replace(/\.md$/i, "");
      const page = pageKey ? dv.page(pageKey) : null;
      const stage = page && hasValue(page.stage) ? String(page.stage) : "—";

      const row = list.createEl("li");
      Object.assign(row.style, {
        display: "flex",
        alignItems: "center",
        gap: "0.35rem",
        marginBottom: "0.3rem"
      });

      row.createEl("input", { type: "checkbox" });
      row.createSpan({ text: ":" });

      const href = target || rawLink;
      const linkText = alias || page?.title || page?.file?.name || target || rawLink;
      const a = row.createEl("a", {
        text: linkText,
        href,
        cls: "internal-link"
      });
      a.setAttr("data-href", href);

      row.createSpan({ text: ":" });
      row.createSpan({ text: stage });
    }
  }
})();
```
