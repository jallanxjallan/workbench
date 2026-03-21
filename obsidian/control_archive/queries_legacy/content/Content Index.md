```dataviewjs
(async () => {
  const SESSION_KEY = "_contentQuerySession";
  const COMMANDS_KEY = "_contentQueryCommands";
  const LIFECYCLE_KEY = "_contentQueryLifecycleBound";
  const SELECTION_KEY = "contentQuerySelections_v1";
  const FIELDS = [
    { key: "class", label: "Class" },
    { key: "stage", label: "Stage" },
    { key: "state", label: "State" },
  ];

  const current = dv.current() ?? {};
  const viewPath = normalizePath(current?.file?.path ?? "");
  const indexNote = normalizeString(current.index_note || "Table of Contents.md");
  const contentRoot = normalizeFolder(current.content_root || "contents/");
  const container = dv?.container ?? this?.container;
  if (!container) return;

  bindLifecycleHooks();

  const filters = createFilterState();
  const selections = loadSelections();
  let session = await ensureSession();
  pruneSelections(selections, session.rows);
  exposeCommandHooks();
  await render();

  async function ensureSession() {
    const existing = window[SESSION_KEY];
    if (
      existing &&
      existing.viewPath === viewPath &&
      existing.indexNote === indexNote &&
      existing.contentRoot === contentRoot
    ) {
      return existing;
    }

    const built = await buildSession({
      viewPath,
      indexNote,
      contentRoot,
    });
    window[SESSION_KEY] = built;
    return built;
  }

  async function buildSession({ viewPath, indexNote, contentRoot }) {
    const pageCache = buildPageCache();
    const tocResolution = resolveIndexFile(indexNote, viewPath);
    const tocText = tocResolution.file
      ? await app.vault.cachedRead(tocResolution.file)
      : "";
    const parsedTOC = tocText ? parseTOC(tocText) : [];
    const gitIndex = await fetchGitIndex();

    const rows = parsedTOC.length
      ? buildTOCRows(parsedTOC, tocResolution.file?.path || viewPath, pageCache)
      : scanFilesystem(contentRoot, pageCache);

    return {
      viewPath,
      indexNote,
      contentRoot,
      tocGroups: parsedTOC,
      rows,
      pageCache,
      gitIndex,
      lastScan: Date.now(),
      sourceKind: parsedTOC.length ? "toc" : "filesystem",
      sourceFile: tocResolution.file ?? null,
      warning: buildSourceWarning(tocResolution, tocText, parsedTOC),
      values: collectFilterValues(rows),
    };
  }

  function buildSourceWarning(tocResolution, tocText, parsedTOC) {
    if (tocResolution.warning) return tocResolution.warning;
    if (tocText && parsedTOC.length === 0) {
      return `No headings with wikilinks were found in "${tocResolution.file?.path || indexNote}". Falling back to ${contentRoot}.`;
    }
    return "";
  }

  function buildPageCache() {
    const cache = new Map();

    for (const file of app.vault.getMarkdownFiles()) {
      const filePath = normalizePath(file.path);
      const page = dv.page(filePath) ?? {};
      const entry = {
        file,
        page,
        filePath,
        title: normalizeString(page.title || file.basename || file.name || filePath),
      };

      cache.set(filePath, entry);
      cache.set(stripMarkdownExtension(filePath), entry);
    }

    return cache;
  }

  function parseTOC(sourceText) {
    const headingRe = /^\s{0,3}#{1,6}\s+(.+?)\s*$/;
    const wikilinkRe = /\[\[([^[\]]+?)\]\]/g;
    const groups = [];
    let currentGroup = null;

    for (const line of String(sourceText || "").split(/\r?\n/)) {
      const headingMatch = line.match(headingRe);
      if (headingMatch) {
        currentGroup = { heading: headingMatch[1].trim(), links: [] };
        groups.push(currentGroup);
        continue;
      }

      let match = null;
      while ((match = wikilinkRe.exec(line)) !== null) {
        if (!currentGroup) {
          currentGroup = { heading: "(No Heading)", links: [] };
          groups.push(currentGroup);
        }
        currentGroup.links.push(match[1].trim());
      }
    }

    return groups.filter((group) => group.links.length > 0);
  }

  function buildTOCRows(groups, fromPath, pageCache) {
    const rows = [];

    for (const group of groups) {
      for (const rawLink of group.links) {
        rows.push(buildRowFromLink(rawLink, group.heading, fromPath, pageCache));
      }
    }

    return rows;
  }

  function scanFilesystem(root, pageCache) {
    return app.vault
      .getMarkdownFiles()
      .filter((file) => normalizePath(file.path).startsWith(root))
      .map((file) => buildRowFromFile("(All Files)", file.path, pageCache))
      .sort((left, right) => left.linkText.localeCompare(right.linkText));
  }

  function buildRowFromLink(rawLink, heading, fromPath, pageCache) {
    const parsed = parseLinkTarget(rawLink);
    const resolved = parsed.pageKey
      ? app.metadataCache.getFirstLinkpathDest(parsed.pageKey, fromPath)
      : null;
    const resolvedPath = normalizePath(resolved?.path || "");
    const cacheEntry = resolvedPath
      ? pageCache.get(resolvedPath) || pageCache.get(stripMarkdownExtension(resolvedPath))
      : pageCache.get(parsed.pageKey) || pageCache.get(ensureMarkdownPath(parsed.pageKey));
    const page = cacheEntry?.page ?? {};
    const filePath = normalizePath(
      resolvedPath || cacheEntry?.filePath || ensureMarkdownPath(parsed.pageKey),
    );
    const hrefBase = normalizePath(
      resolvedPath ? stripMarkdownExtension(resolvedPath) : parsed.pageKey,
    );
    const href = buildHref(hrefBase, parsed.anchor, parsed.blockRef);
    const linkText = normalizeString(
      parsed.alias ||
        page.title ||
        cacheEntry?.file?.basename ||
        parsed.pageKey ||
        rawLink,
    );

    return {
      heading,
      filePath,
      linkText,
      href,
      class: toValueList(page.class),
      stage: toValueList(page.stage),
      state: toValueList(page.state),
    };
  }

  function buildRowFromFile(heading, filePath, pageCache) {
    const cleanPath = normalizePath(filePath);
    const cacheEntry =
      pageCache.get(cleanPath) || pageCache.get(stripMarkdownExtension(cleanPath));
    const page = cacheEntry?.page ?? {};

    return {
      heading,
      filePath: cleanPath,
      linkText: normalizeString(
        page.title || cacheEntry?.file?.basename || cleanPath,
      ),
      href: stripMarkdownExtension(cleanPath),
      class: toValueList(page.class),
      stage: toValueList(page.stage),
      state: toValueList(page.state),
    };
  }

  async function fetchGitIndex() {
    return {
      staged: new Set(),
      modified: new Set(),
    };
  }

  function filterRows(session, activeFilters) {
    const search = normalizeString(activeFilters.search).toLowerCase();

    return session.rows.filter((row) => {
      if (session.gitIndex.staged.has(row.filePath)) return false;
      if (!matchesFilter(row.class, activeFilters.class)) return false;
      if (!matchesFilter(row.stage, activeFilters.stage)) return false;
      if (!matchesFilter(row.state, activeFilters.state)) return false;
      if (!matchesSearch(row, search)) return false;
      return true;
    });
  }

  function matchesFilter(rowValues, selectedValues) {
    if (!selectedValues || selectedValues.size === 0) return true;
    if (!Array.isArray(rowValues) || rowValues.length === 0) return false;
    return rowValues.some((value) => selectedValues.has(value));
  }

  function matchesSearch(row, search) {
    if (!search) return true;

    const haystack = [
      row.heading,
      row.filePath,
      row.linkText,
      ...(row.class || []),
      ...(row.stage || []),
      ...(row.state || []),
    ]
      .map((value) => normalizeString(value).toLowerCase())
      .join(" ");

    return haystack.includes(search);
  }

  function groupRows(rows) {
    const groups = [];
    let currentGroup = null;

    for (const row of rows) {
      if (!currentGroup || currentGroup.heading !== row.heading) {
        currentGroup = { heading: row.heading, rows: [] };
        groups.push(currentGroup);
      }
      currentGroup.rows.push(row);
    }

    return groups;
  }

  async function render() {
    session = await ensureSession();
    window[COMMANDS_KEY] = createCommandHooks();
    pruneSelections(selections, session.rows);

    const filteredRows = filterRows(session, filters);
    const groupedRows = groupRows(filteredRows);
    const selectedOrdered = getOrderedSelectedPaths(session.rows, selections);
    const visibleSelected = filteredRows.filter((row) => selections.has(row.filePath)).length;

    container.empty();

    renderHeader(container, session);
    renderFilters(container, session.values, filters, async () => {
      await render();
    });

    container.createEl("hr");

    const summary = container.createDiv();
    Object.assign(summary.style, { marginBottom: "0.75rem" });
    summary.setText(buildSummaryText(session, filteredRows, selectedOrdered.length, visibleSelected));

    if (groupedRows.length === 0) {
      container.createDiv({
        text: "No files match the current filter set.",
      });
      renderFooter(container, session, filteredRows);
      return;
    }

    for (const group of groupedRows) {
      renderGroup(container, group, async () => {
        toggleGroupSelection(group.rows);
        await render();
      });
    }

    renderFooter(container, session, filteredRows);
  }

  function renderHeader(parent, session) {
    const title = parent.createEl("h2", { text: "Content Query" });
    Object.assign(title.style, { margin: "0 0 0.5rem 0" });

    const sourceInfo = parent.createDiv();
    Object.assign(sourceInfo.style, {
      marginBottom: session.warning ? "0.4rem" : "0.75rem",
      opacity: "0.85",
    });

    if (session.sourceKind === "toc" && session.sourceFile) {
      sourceInfo.append("Source: ");
      appendInternalLink(
        sourceInfo,
        stripMarkdownExtension(session.sourceFile.path),
        session.sourceFile.basename,
      );
      sourceInfo.append(` (${session.rows.length} row${session.rows.length === 1 ? "" : "s"})`);
    } else {
      sourceInfo.setText(`Source: filesystem fallback (${session.contentRoot})`);
    }

    if (session.warning) {
      const warning = parent.createDiv({ text: session.warning });
      Object.assign(warning.style, {
        marginBottom: "0.75rem",
        color: "var(--text-warning, #b26a00)",
      });
    }
  }

  function renderFilters(parent, valuesByField, activeFilters, onChange) {
    for (const { key, label } of FIELDS) {
      const row = parent.createDiv();
      Object.assign(row.style, {
        display: "flex",
        alignItems: "center",
        flexWrap: "wrap",
        gap: "0.4rem",
        marginBottom: "0.35rem",
      });

      row.createEl("strong", { text: `${label}:` });

      const selectAll = row.createEl("button", { text: "Select All" });
      selectAll.type = "button";
      selectAll.addEventListener("click", async () => {
        activeFilters[key] = new Set(valuesByField[key]);
        await onChange();
      });

      const clear = row.createEl("button", { text: "Clear" });
      clear.type = "button";
      clear.addEventListener("click", async () => {
        activeFilters[key] = new Set();
        await onChange();
      });

      if ((valuesByField[key]?.length ?? 0) === 0) {
        row.createSpan({ text: "(none)" });
        continue;
      }

      for (const value of valuesByField[key]) {
        const token = row.createEl("button", { text: value });
        token.type = "button";
        styleFilterToken(token, activeFilters[key].has(value));
        token.addEventListener("click", async () => {
          if (activeFilters[key].has(value)) activeFilters[key].delete(value);
          else activeFilters[key].add(value);
          await onChange();
        });
      }
    }

    const searchRow = parent.createDiv();
    Object.assign(searchRow.style, {
      display: "flex",
      alignItems: "center",
      gap: "0.5rem",
      marginTop: "0.25rem",
      flexWrap: "wrap",
    });

    searchRow.createEl("strong", { text: "Search:" });

    const input = searchRow.createEl("input", {
      type: "text",
      placeholder: "title, path, class, stage",
    });
    input.value = activeFilters.search;
    Object.assign(input.style, {
      minWidth: "16rem",
      padding: "0.2rem 0.35rem",
    });
    input.addEventListener("change", async () => {
      activeFilters.search = input.value;
      await onChange();
    });

    const clearSearch = searchRow.createEl("button", { text: "Clear Search" });
    clearSearch.type = "button";
    clearSearch.addEventListener("click", async () => {
      activeFilters.search = "";
      await onChange();
    });
  }

  function renderGroup(parent, group, onToggle) {
    const headingRow = parent.createDiv();
    Object.assign(headingRow.style, {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      gap: "0.75rem",
      margin: "0.75rem 0 0.35rem 0",
      flexWrap: "wrap",
    });

    headingRow.createEl("h3", { text: group.heading });
    Object.assign(headingRow.lastChild.style, { margin: "0" });

    const uniquePaths = [...new Set(group.rows.map((row) => row.filePath).filter(Boolean))];
    const allSelected = uniquePaths.length > 0 && uniquePaths.every((path) => selections.has(path));

    const toggle = headingRow.createEl("button", {
      text: allSelected ? "Clear All" : "Select All",
    });
    toggle.type = "button";
    toggle.addEventListener("click", onToggle);

    const list = parent.createEl("ul");
    Object.assign(list.style, {
      listStyle: "none",
      padding: "0",
      margin: "0 0 1rem 0",
    });

    for (const row of group.rows) {
      const item = list.createEl("li");
      item.setAttribute("data-file-path", row.filePath || "");
      Object.assign(item.style, {
        display: "flex",
        alignItems: "center",
        gap: "0.4rem",
        marginBottom: "0.35rem",
        paddingLeft: isCaptionRow(row) ? "1.25rem" : "0",
      });

      const checkbox = item.createEl("input", { type: "checkbox" });
      checkbox.checked = selections.has(row.filePath);
      checkbox.addEventListener("change", async () => {
        if (checkbox.checked) selections.add(row.filePath);
        else selections.delete(row.filePath);
        saveSelections(selections);
        await render();
      });

      appendInternalLink(item, row.href || row.filePath, row.linkText);
      renderMetadataLabels(item, row);
    }
  }

  function renderMetadataLabels(parent, row) {
    const values = [...(row.class || [])];
    if (values.length === 0) return;

    const label = parent.createSpan({
      text: `[${values.join(", ")}]`,
    });
    Object.assign(label.style, {
      opacity: "0.75",
      fontSize: "0.9em",
    });
  }

  function renderFooter(parent, session, filteredRows) {
    parent.createEl("hr");

    const footerRow = parent.createDiv();
    Object.assign(footerRow.style, {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      gap: "0.75rem",
      marginTop: "0.5rem",
      flexWrap: "wrap",
    });

    const meta = footerRow.createDiv({
      text: `Selected: ${getOrderedSelectedPaths(session.rows, selections).length} total, ${filteredRows.filter((row) => selections.has(row.filePath)).length} visible`,
    });
    Object.assign(meta.style, { opacity: "0.8" });

    const controls = footerRow.createDiv();
    Object.assign(controls.style, {
      display: "flex",
      gap: "0.4rem",
      flexWrap: "wrap",
    });

    const clearSelection = controls.createEl("button", { text: "Clear Selection" });
    clearSelection.type = "button";
    clearSelection.addEventListener("click", async () => {
      selections.clear();
      saveSelections(selections);
      await render();
    });

    const processBtn = controls.createEl("button", { text: "Process" });
    processBtn.type = "button";
    processBtn.addEventListener("click", async () => {
      const paths = await window[COMMANDS_KEY].process();
      if (paths.length === 0 && typeof Notice === "function") {
        new Notice("No files selected.");
      }
    });

    const submitBtn = controls.createEl("button", { text: "Submit" });
    submitBtn.type = "button";
    submitBtn.addEventListener("click", async () => {
      const paths = await window[COMMANDS_KEY].submit();
      if (paths.length === 0 && typeof Notice === "function") {
        new Notice("No files selected.");
      }
    });
  }

  function buildSummaryText(session, filteredRows, selectedTotal, selectedVisible) {
    const hiddenByGit = session.rows.length - session.rows.filter(
      (row) => !session.gitIndex.staged.has(row.filePath),
    ).length;

    const parts = [
      `Showing ${filteredRows.length} of ${session.rows.length} row${session.rows.length === 1 ? "" : "s"}`,
      `selected ${selectedTotal} total`,
    ];

    if (selectedVisible !== selectedTotal) {
      parts.push(`${selectedVisible} visible`);
    }

    if (hiddenByGit > 0) {
      parts.push(`${hiddenByGit} hidden by git staging`);
    }

    return parts.join(" | ");
  }

  function createFilterState() {
    const state = { search: "" };
    for (const { key } of FIELDS) state[key] = new Set();
    return state;
  }

  function collectFilterValues(rows) {
    return Object.fromEntries(
      FIELDS.map(({ key }) => [key, collectUniqueValues(rows, key)]),
    );
  }

  function collectUniqueValues(sourceRows, field) {
    const set = new Set();
    for (const row of sourceRows) {
      for (const value of row[field] || []) set.add(value);
    }
    return [...set].sort((left, right) => left.localeCompare(right));
  }

  function parseLinkTarget(rawLink) {
    const [targetPart, aliasPart] = String(rawLink || "").split("|");
    const target = normalizeString(targetPart);
    const alias = normalizeString(aliasPart);
    const [targetWithoutBlock, blockRef = ""] = target.split("^");
    const [targetWithoutAnchor, anchor = ""] = targetWithoutBlock.split("#");
    const pageKey = stripMarkdownExtension(normalizePath(targetWithoutAnchor));

    return {
      target,
      alias,
      anchor: normalizeString(anchor),
      blockRef: normalizeString(blockRef),
      pageKey,
    };
  }

  function resolveIndexFile(indexNote, fromPath) {
    const base = normalizePath(indexNote);
    const baseNoExt = stripMarkdownExtension(base);
    const baseName = baseNoExt.split("/").pop() || "";

    const pathCandidates = /\.md$/i.test(base) ? [base] : [`${base}.md`, base];
    for (const candidate of pathCandidates) {
      const exact = app.vault.getFileByPath(candidate);
      if (exact) return { file: exact, warning: "" };
    }

    for (const candidate of [baseNoExt, baseName].filter(Boolean)) {
      const resolved = app.metadataCache.getFirstLinkpathDest(candidate, fromPath);
      if (resolved) return { file: resolved, warning: "" };
    }

    if (baseName) {
      const matches = app.vault
        .getMarkdownFiles()
        .filter(
          (file) =>
            normalizeString(file.basename).toLowerCase() === baseName.toLowerCase(),
        );

      if (matches.length === 1) {
        return { file: matches[0], warning: "" };
      }

      if (matches.length > 1) {
        return {
          file: null,
          warning: `Multiple files named "${baseName}.md" were found. Set frontmatter index_note to an exact vault path. Falling back to ${contentRoot}.`,
        };
      }
    }

    return {
      file: null,
      warning: `Could not resolve "${indexNote}". Falling back to ${contentRoot}.`,
    };
  }

  function exposeCommandHooks() {
    window[COMMANDS_KEY] = createCommandHooks();
  }

  function createCommandHooks() {
    const getSelectedFilePaths = async () => {
      session = await ensureSession();
      pruneSelections(selections, session.rows);
      return getOrderedSelectedPaths(session.rows, selections);
    };

    return {
      getSelectedFilePaths,
      process: async () => {
        const paths = await getSelectedFilePaths();
        if (paths?.length && typeof Notice === "function") {
          new Notice(`Process stub: ${paths.length} file${paths.length === 1 ? "" : "s"}.`);
        }
        console.log("Content Query Process:", paths || []);
        return paths || [];
      },
      submit: async () => {
        const paths = await getSelectedFilePaths();
        if (paths?.length && typeof Notice === "function") {
          new Notice(`Submit stub: ${paths.length} file${paths.length === 1 ? "" : "s"}.`);
        }
        console.log("Content Query Submit:", paths || []);
        return paths || [];
      },
    };
  }

  function getOrderedSelectedPaths(rows, selectionSet) {
    const ordered = [];
    const seen = new Set();

    for (const row of rows) {
      if (!row.filePath || !selectionSet.has(row.filePath) || seen.has(row.filePath)) {
        continue;
      }
      seen.add(row.filePath);
      ordered.push(row.filePath);
    }

    return ordered;
  }

  function toggleGroupSelection(groupRows) {
    const filePaths = [...new Set(groupRows.map((row) => row.filePath).filter(Boolean))];
    const allSelected = filePaths.length > 0 && filePaths.every((path) => selections.has(path));

    for (const filePath of filePaths) {
      if (allSelected) selections.delete(filePath);
      else selections.add(filePath);
    }

    saveSelections(selections);
  }

  function loadSelections() {
    try {
      const parsed = JSON.parse(localStorage.getItem(SELECTION_KEY) || "[]");
      return new Set((Array.isArray(parsed) ? parsed : []).map(normalizePath).filter(Boolean));
    } catch {
      return new Set();
    }
  }

  function saveSelections(selectionSet) {
    localStorage.setItem(SELECTION_KEY, JSON.stringify([...selectionSet]));
  }

  function pruneSelections(selectionSet, rows) {
    const validPaths = new Set(rows.map((row) => row.filePath).filter(Boolean));
    let changed = false;

    for (const filePath of [...selectionSet]) {
      if (!validPaths.has(filePath)) {
        selectionSet.delete(filePath);
        changed = true;
      }
    }

    if (changed) saveSelections(selectionSet);
  }

  function appendInternalLink(parent, href, text) {
    const cleanHref = normalizeString(href);
    const link = parent.createEl("a", {
      text: text || cleanHref,
      href: cleanHref,
      cls: "internal-link",
    });
    link.setAttr("data-href", cleanHref);
    return link;
  }

  function styleFilterToken(button, isActive) {
    Object.assign(button.style, {
      cursor: "pointer",
      fontWeight: isActive ? "700" : "400",
      textDecoration: isActive ? "underline" : "none",
      padding: "0.05rem 0.35rem",
    });
  }

  function isCaptionRow(row) {
    return (row.class || []).some((value) => value.toLowerCase() === "caption");
  }

  function buildHref(base, anchor, blockRef) {
    const cleanBase = normalizeString(base);
    if (!cleanBase) return "";
    if (anchor) return `${cleanBase}#${anchor}`;
    if (blockRef) return `${cleanBase}^${blockRef}`;
    return cleanBase;
  }

  function toValueList(value) {
    if (Array.isArray(value)) return value.map(normalizeString).filter(Boolean);
    const single = normalizeString(value);
    return single ? [single] : [];
  }

  function normalizeFolder(value) {
    const normalized = normalizePath(value);
    return normalized ? `${normalized.replace(/\/+$/, "")}/` : "contents/";
  }

  function normalizePath(value) {
    return String(value ?? "").trim().replace(/\\/g, "/").replace(/^\/+/, "");
  }

  function normalizeString(value) {
    return String(value ?? "").trim();
  }

  function stripMarkdownExtension(value) {
    return normalizePath(value).replace(/\.md$/i, "");
  }

  function ensureMarkdownPath(value) {
    const clean = stripMarkdownExtension(value);
    return clean ? `${clean}.md` : "";
  }

  function bindLifecycleHooks() {
    if (window[LIFECYCLE_KEY]) return;

    const invalidate = () => {
      delete window[SESSION_KEY];
      delete window[COMMANDS_KEY];
    };

    window[LIFECYCLE_KEY] = true;
    window.addEventListener("blur", invalidate);
    window.addEventListener("beforeunload", invalidate);
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") invalidate();
    });
  }
})();
```
