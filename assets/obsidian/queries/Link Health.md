
```dataviewjs
(() => {
  const current = dv.current?.() ?? {};
  const normalizePath = (value) =>
    String(value ?? "").trim().replace(/\\/g, "/").replace(/^\/+/, "");
  const stripExt = (value) => String(value ?? "").replace(/\.md$/i, "");
  const isMarkdownPath = (value) => /\.md$/i.test(String(value ?? "").trim());
  const INDEX_NOTE = String(current.index_note ?? "Table of Contents.md").trim();
  const CONTENT_ROOT = normalizeFolder(String(current.content_root ?? "content/").trim());

  const container = dv?.container ?? this?.container;
  if (container) container.empty();

  const toc = resolveIndexFile(INDEX_NOTE, dv.current().file.path);

  // 1) Files with unresolved internal links (broken links)
  dv.header(2, "Files with broken links");
  const brokenByFile = collectBrokenLinks(app);
  if (brokenByFile.length === 0) {
    dv.paragraph("No files with broken links.");
  } else {
    dv.table(
      ["File", "Broken targets", "Total"],
      brokenByFile.map((row) => [
        dv.fileLink(row.path),
        row.targets.join(", "),
        row.totalCount,
      ]),
    );
  }

  // 2) content/ files not linked from the Table of Contents note
  dv.header(2, `Files in ${CONTENT_ROOT || "content/"} not linked from the Table of Contents`);
  if (!CONTENT_ROOT) {
    dv.paragraph("Set frontmatter content_root to a folder, for example: content/");
    return;
  }

  if (!toc.file) {
    dv.paragraph(toc.error || `Could not resolve index note "${INDEX_NOTE}".`);
    return;
  }

  const contentPaths = app.vault
    .getMarkdownFiles()
    .map((file) => normalizePath(file.path))
    .filter((path) => path.startsWith(CONTENT_ROOT))
    .filter((path) => normalizePath(toc.file.path) !== path);

  const linkedContent = collectLinkedContentFromToc({
    app,
    tocPath: toc.file.path,
    contentRoot: CONTENT_ROOT,
    normalizePath,
    stripExt,
  });

  const unlinked = contentPaths
    .filter((path) => !linkedContent.has(path))
    .sort((a, b) => a.localeCompare(b));

  dv.paragraph(
    [
      `Table of Contents: ${dv.fileLink(toc.file.path)}`,
      `content/ files: ${contentPaths.length}`,
      `linked from TOC: ${contentPaths.length - unlinked.length}`,
      `not linked from TOC: ${unlinked.length}`,
    ].join(" | "),
  );

  if (unlinked.length === 0) {
    dv.paragraph("All files in the content folder are linked from the Table of Contents.");
    return;
  }

  dv.table(["File"], unlinked.map((path) => [dv.fileLink(path)]));

  function resolveIndexFile(indexNote, fromPath) {
    const base = normalizePath(indexNote);
    const baseNoExt = stripExt(base);
    const baseNameNoExt = stripExt(baseNoExt.split("/").pop() ?? "");

    let sourceFile = null;

    const pathCandidates = base.endsWith(".md") ? [base] : [`${base}.md`, base];
    for (const candidate of pathCandidates) {
      const file = app.vault.getFileByPath(candidate);
      if (file) {
        sourceFile = file;
        break;
      }
    }

    if (!sourceFile) {
      const linkCandidates = [baseNoExt, baseNameNoExt].filter(Boolean);
      for (const candidate of linkCandidates) {
        const file = app.metadataCache.getFirstLinkpathDest(candidate, fromPath);
        if (file) {
          sourceFile = file;
          break;
        }
      }
    }

    if (!sourceFile && baseNameNoExt) {
      const matches = app.vault
        .getMarkdownFiles()
        .filter(
          (file) =>
            String(file.basename ?? "").toLowerCase() === baseNameNoExt.toLowerCase(),
        );
      if (matches.length === 1) {
        sourceFile = matches[0];
      } else if (matches.length > 1) {
        return {
          file: null,
          error: `Multiple files named "${baseNameNoExt}.md" found. Set frontmatter index_note to an exact vault path.`,
        };
      }
    }

    if (!sourceFile) {
      return {
        file: null,
        error: `Could not resolve "${indexNote}". Set frontmatter index_note to an exact path, e.g. "Table of Contents.md".`,
      };
    }

    return { file: sourceFile };
  }

  function collectBrokenLinks(appRef) {
    const unresolved = appRef?.metadataCache?.unresolvedLinks ?? {};
    const rows = [];

    for (const [sourcePathRaw, targetMapRaw] of Object.entries(unresolved)) {
      const sourcePath = normalizePath(sourcePathRaw);
      if (!isMarkdownPath(sourcePath)) continue;

      const targetEntries = Object.entries(targetMapRaw ?? {})
        .filter(([target]) => String(target ?? "").trim().length > 0)
        .map(([target, count]) => ({
          target: String(target).trim(),
          count: Number(count ?? 0),
        }))
        .filter((entry) => entry.count > 0)
        .sort((a, b) => b.count - a.count || a.target.localeCompare(b.target));

      if (targetEntries.length === 0) continue;

      rows.push({
        path: sourcePath,
        targets: targetEntries.map((entry) =>
          entry.count > 1 ? `${entry.target} (${entry.count}x)` : entry.target,
        ),
        totalCount: targetEntries.reduce((sum, entry) => sum + entry.count, 0),
      });
    }

    rows.sort((a, b) => b.totalCount - a.totalCount || a.path.localeCompare(b.path));
    return rows;
  }

  function collectLinkedContentFromToc(args) {
    const { app: appRef, tocPath, contentRoot, normalizePath, stripExt } = args;
    const file = appRef.vault.getFileByPath(tocPath);
    if (!file) return new Set();

    const cache = appRef.metadataCache.getFileCache(file) ?? {};
    const links = Array.isArray(cache.links) ? cache.links : [];
    const linked = new Set();

    for (const linkEntry of links) {
      const raw = String(linkEntry?.link ?? "").trim();
      if (!raw) continue;

      const withoutSubpath = raw.split("#")[0].split("^")[0].trim();
      const candidate = stripExt(withoutSubpath);
      if (!candidate) continue;

      const resolved = appRef.metadataCache.getFirstLinkpathDest(candidate, tocPath);
      if (!resolved?.path) continue;

      const path = normalizePath(resolved.path);
      if (path.startsWith(contentRoot)) linked.add(path);
    }

    return linked;
  }

  function normalizeFolder(folder) {
    const clean = normalizePath(folder).replace(/\/+$/, "");
    return clean ? `${clean}/` : "";
  }
})();
```
