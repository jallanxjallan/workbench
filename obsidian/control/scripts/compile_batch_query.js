(async () => {
  const fs = require("fs");
  const path = require("path");
  const SESSION_KEY = "_compileBatchSession";
  const COMMANDS_KEY = "_compileBatchCommands";
  const LIFECYCLE_KEY = "_compileBatchLifecycleBound";
  const SELECTION_KEY = "compileBatchSelections_v2";
  const FIELDS = [
    { key: "class", label: "Class" },
    { key: "stage", label: "Stage" },
    { key: "status", label: "Status" },
  ];

  const current = dv.current() ?? {};
  const viewPath = normalizePath(current?.file?.path ?? "");
  const indexNote = normalizeString(current.index_note || "");
  const containerEl =
    (typeof container !== "undefined" && container) || dv?.container || this?.container;
  if (!containerEl) return;

  bindLifecycleHooks();

  const filters = createFilterState();
  const selections = restoreSelections();
  let session = await ensureSession();
  pruneSelections(selections, session.rows);
  window[COMMANDS_KEY] = createCommandHooks();
  await render();

  async function ensureSession() {
    const existing = window[SESSION_KEY];
    if (existing && existing.viewPath === viewPath && existing.indexNote === indexNote) {
      return existing;
    }

    const built = await buildSession();
    window[SESSION_KEY] = built;
    return built;
  }

  async function buildSession() {
    const pageCache = buildPageCache();
    const tocResolution = indexNote ? resolveIndexFile(indexNote, viewPath) : { file: null, warning: "" };
    const tocText = tocResolution.file ? await app.vault.cachedRead(tocResolution.file) : "";
    const tocGroups = tocText ? parseTOC(tocText) : [];
    const rows = tocGroups.length
      ? buildRowsFromTOC(tocGroups, tocResolution.file?.path || viewPath, pageCache)
      : scanVault(pageCache);

    return {
      viewPath,
      indexNote,
      tocGroups,
      rows,
      pageCache,
      sourceKind: tocGroups.length ? "toc" : "vault",
      sourceFile: tocResolution.file ?? null,
      warning: buildSourceWarning(tocResolution, tocText, tocGroups),
      values: collectFilterValues(rows),
    };
  }

  function buildPageCache() {
    const cache = new Map();

    for (const file of app.vault.getMarkdownFiles()) {
      const filePath = normalizePath(file.path);
      if (isControlPath(filePath)) continue;

      const page = dv.page(filePath) ?? {};
      const entry = { file, page, filePath };
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

  function scanVault(pageCache) {
    return [...new Set(pageCache.values())]
      .map((entry) => buildRow("(All Notes)", entry.filePath, pageCache))
      .filter((row) => row.filePath)
      .sort((left, right) => left.linkText.localeCompare(right.linkText));
  }

  function buildRowsFromTOC(groups, fromPath, pageCache) {
    const rows = [];
    for (const group of groups) {
      for (const rawLink of group.links) {
        rows.push(buildRowFromLink(group.heading, rawLink, fromPath, pageCache));
      }
    }
    return rows.filter((row) => row.filePath);
  }

  function buildRowFromLink(heading, rawLink, fromPath, pageCache) {
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

    if (isControlPath(filePath)) {
      return emptyRow();
    }

    return {
      heading,
      filePath,
      linkText: normalizeString(
        parsed.alias || page.title || cacheEntry?.file?.basename || parsed.pageKey || rawLink,
      ),
      href: buildHref(
        resolvedPath ? stripMarkdownExtension(resolvedPath) : parsed.pageKey,
        parsed.anchor,
        parsed.blockRef,
      ),
      class: toValueList(page.class),
      stage: toValueList(page.stage),
      status: toValueList(page.status),
      slug: normalizeString(page.slug),
    };
  }

  function buildRow(heading, filePath, pageCache) {
    const cleanPath = normalizePath(filePath);
    if (isControlPath(cleanPath)) {
      return emptyRow();
    }

    const cacheEntry = pageCache.get(cleanPath) || pageCache.get(stripMarkdownExtension(cleanPath));
    const page = cacheEntry?.page ?? {};

    return {
      heading,
      filePath: cleanPath,
      linkText: normalizeString(page.title || cacheEntry?.file?.basename || cleanPath),
      href: stripMarkdownExtension(cleanPath),
      class: toValueList(page.class),
      stage: toValueList(page.stage),
      status: toValueList(page.status),
      slug: normalizeString(page.slug),
    };
  }

  function emptyRow() {
    return {
      heading: "",
      filePath: "",
      linkText: "",
      href: "",
      class: [],
      stage: [],
      status: [],
      slug: "",
    };
  }

  function filterRows(sourceSession, activeFilters) {
    const search = normalizeString(activeFilters.search).toLowerCase();

    return sourceSession.rows.filter((row) => {
      if (!matchesFilter(row.class, activeFilters.class)) return false;
      if (!matchesFilter(row.stage, activeFilters.stage)) return false;
      if (!matchesFilter(row.status, activeFilters.status)) return false;
      if (!matchesSearch(row, search)) return false;
      return true;
    });
  }

  async function render() {
    session = await ensureSession();
    pruneSelections(selections, session.rows);
    window[COMMANDS_KEY] = createCommandHooks();

    const filteredRows = filterRows(session, filters);
    const groupedRows = groupRows(filteredRows);
    const selectedPaths = getOrderedSelectedPaths(session.rows, selections);

    containerEl.empty();
    renderHeader(containerEl, session, filteredRows.length, selectedPaths.length);
    renderFilters(containerEl, session.values, filters, render);

    containerEl.createEl("hr");

    if (groupedRows.length === 0) {
      containerEl.createDiv({ text: "No files match the current filter set." });
      renderFooter(containerEl);
      return;
    }

    for (const group of groupedRows) {
      renderHeading(containerEl, group, async () => {
        toggleGroupSelection(group.rows);
        await render();
      });

      const list = containerEl.createEl("ul");
      Object.assign(list.style, {
        listStyle: "none",
        padding: "0",
        margin: "0 0 1rem 0",
      });

      for (const row of group.rows) {
        renderRow(list, row, render);
      }
    }

    renderFooter(containerEl);
  }

  function renderHeading(parent, group, onToggle) {
    const headingRow = parent.createDiv();
    Object.assign(headingRow.style, {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      gap: "0.75rem",
      margin: "0.75rem 0 0.35rem 0",
      flexWrap: "wrap",
    });

    const title = headingRow.createEl("h3", { text: group.heading });
    Object.assign(title.style, { margin: "0" });

    const paths = [...new Set(group.rows.map((row) => row.filePath).filter(Boolean))];
    const allSelected = paths.length > 0 && paths.every((filePath) => selections.has(filePath));
    const toggle = headingRow.createEl("button", {
      text: allSelected ? "Clear All" : "Select All",
    });
    toggle.type = "button";
    toggle.addEventListener("click", onToggle);
  }

  function renderRow(parent, row, onChange) {
    const item = parent.createEl("li");
    Object.assign(item.style, {
      display: "flex",
      alignItems: "center",
      gap: "0.4rem",
      marginBottom: "0.35rem",
    });

    const checkbox = item.createEl("input", { type: "checkbox" });
    checkbox.checked = selections.has(row.filePath);
    checkbox.addEventListener("change", async () => {
      if (checkbox.checked) selections.add(row.filePath);
      else selections.delete(row.filePath);
      saveSelections(selections);
      await onChange();
    });

    appendInternalLink(item, row.href || row.filePath, row.linkText);

    const labels = [
      ...(row.class || []).map((value) => `[${value}]`),
      ...(row.slug ? [`slug:${row.slug}`] : []),
    ];
    if (labels.length > 0) {
      const label = item.createSpan({ text: labels.join(" ") });
      Object.assign(label.style, { opacity: "0.75", fontSize: "0.9em" });
    }
  }

  function renderHeader(parent, sourceSession, visibleCount, selectedCount) {
    const title = parent.createEl("h2", { text: "Compile Batch" });
    Object.assign(title.style, { margin: "0 0 0.5rem 0" });

    const summary = parent.createDiv();
    Object.assign(summary.style, { marginBottom: sourceSession.warning ? "0.4rem" : "0.75rem" });

    const sourceLabel = sourceSession.sourceKind === "toc" && sourceSession.sourceFile
      ? `Source: ${sourceSession.sourceFile.path}`
      : "Source: vault-wide fallback";
    summary.setText(
      `${sourceLabel} | showing ${visibleCount} of ${sourceSession.rows.length} | selected ${selectedCount}`,
    );

    if (sourceSession.warning) {
      const warning = parent.createDiv({ text: sourceSession.warning });
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

      for (const value of valuesByField[key] || []) {
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
      placeholder: "title, path, class, stage, status, slug",
    });
    input.value = activeFilters.search;
    Object.assign(input.style, { minWidth: "16rem", padding: "0.2rem 0.35rem" });
    input.addEventListener("input", async () => {
      activeFilters.search = input.value;
      await onChange();
    });
  }

  function renderFooter(parent) {
    parent.createEl("hr");

    const row = parent.createDiv();
    Object.assign(row.style, {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      gap: "0.75rem",
      marginTop: "0.5rem",
      flexWrap: "wrap",
    });

    const meta = row.createDiv({
      text: `Selected: ${getOrderedSelectedPaths(session.rows, selections).length} total`,
    });
    Object.assign(meta.style, { opacity: "0.8" });

    const controls = row.createDiv();
    Object.assign(controls.style, { display: "flex", gap: "0.4rem", flexWrap: "wrap" });

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
      if (paths.length === 0 && typeof Notice === "function") new Notice("No files selected.");
    });

    const submitBtn = controls.createEl("button", { text: "Submit" });
    submitBtn.type = "button";
    submitBtn.addEventListener("click", async () => {
      const paths = await window[COMMANDS_KEY].submit();
      if (paths.length === 0 && typeof Notice === "function") new Notice("No files selected.");
    });
  }

  function restoreSelections() {
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

  function writeBatchFile(paths, rows) {
    const vaultBase =
      (app?.vault?.adapter && typeof app.vault.adapter.getBasePath === "function"
        ? app.vault.adapter.getBasePath()
        : app?.vault?.adapter?.basePath) || "";
    if (!vaultBase) {
      throw new Error("vault base path is unavailable");
    }

    const stagingDir = path.join(String(vaultBase), "_staging");
    if (!fs.existsSync(stagingDir)) {
      fs.mkdirSync(stagingDir, { recursive: true });
    }

    const now = new Date();
    const timestamp = formatBatchTimestamp(now);
    const rand = buildSuffix(4);
    const filename = `batch_${timestamp}_${rand}.json`;
    const fullPath = path.join(stagingDir, filename);
    const rowByPath = new Map(rows.map((row) => [row.filePath, row]));

    const payload = {
      version: 1,
      generated_at: now.toISOString(),
      vault_root: String(vaultBase),
      ordered: true,
      count: paths.length,
      files: paths.map((filePath) => {
        const row = rowByPath.get(filePath);
        const slug = normalizeString(row?.slug);
        return {
          path: filePath,
          slug: slug || null,
        };
      }),
    };

    fs.writeFileSync(fullPath, JSON.stringify(payload, null, 2) + "\n", "utf8");
    return fullPath;
  }

  function formatBatchTimestamp(date) {
    const year = String(date.getUTCFullYear());
    const month = String(date.getUTCMonth() + 1).padStart(2, "0");
    const day = String(date.getUTCDate()).padStart(2, "0");
    const hour = String(date.getUTCHours()).padStart(2, "0");
    const minute = String(date.getUTCMinutes()).padStart(2, "0");
    const second = String(date.getUTCSeconds()).padStart(2, "0");
    return `${year}${month}${day}-${hour}${minute}${second}`;
  }

  function buildSuffix(length) {
    const alphabet = "abcdefghijklmnopqrstuvwxyz";
    let out = "";
    for (let index = 0; index < length; index += 1) {
      out += alphabet[Math.floor(Math.random() * alphabet.length)];
    }
    return out;
  }

  function createCommandHooks() {
    const getSelectedFilePaths = async () => {
      session = await ensureSession();
      pruneSelections(selections, session.rows);
      return getOrderedSelectedPaths(session.rows, selections);
    };

    const writeSelectionFile = async (label) => {
      const paths = await getSelectedFilePaths();
      if (paths.length === 0) {
        return [];
      }

      const file = writeBatchFile(paths, session.rows);
      if (typeof Notice === "function") {
        new Notice(`${label}: batch file written -> ${file}`, 8000);
      }
      return { paths, file };
    };

    return {
      getSelectedFilePaths,
      process: async () => writeSelectionFile("Process"),
      submit: async () => writeSelectionFile("Submit"),
    };
  }

  function resolveIndexFile(notePath, fromPath) {
    const normalized = normalizePath(notePath);
    const withoutExt = stripMarkdownExtension(normalized);
    const basename = withoutExt.split("/").pop() || "";

    for (const candidate of /\.md$/i.test(normalized) ? [normalized] : [`${normalized}.md`, normalized]) {
      const exact = app.vault.getFileByPath(candidate);
      if (exact && !isControlPath(exact.path)) return { file: exact, warning: "" };
    }

    for (const candidate of [withoutExt, basename].filter(Boolean)) {
      const resolved = app.metadataCache.getFirstLinkpathDest(candidate, fromPath);
      if (resolved && !isControlPath(resolved.path)) return { file: resolved, warning: "" };
    }

    if (basename) {
      const matches = app.vault.getMarkdownFiles().filter(
        (file) =>
          !isControlPath(file.path) &&
          normalizeString(file.basename).toLowerCase() === basename.toLowerCase(),
      );
      if (matches.length === 1) return { file: matches[0], warning: "" };
      if (matches.length > 1) {
        return {
          file: null,
          warning: `Multiple files named "${basename}.md" were found. Set frontmatter index_note to an exact vault path. Falling back to vault-wide scan.`,
        };
      }
    }

    return {
      file: null,
      warning: `Could not resolve "${notePath}". Falling back to vault-wide scan.`,
    };
  }

  function buildSourceWarning(tocResolution, tocText, tocGroups) {
    if (tocResolution.warning) return tocResolution.warning;
    if (tocText && tocGroups.length === 0) {
      return `No headings with wikilinks were found in "${tocResolution.file?.path || indexNote}". Falling back to vault-wide scan.`;
    }
    return "";
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

  function getOrderedSelectedPaths(rows, selectionSet) {
    const ordered = [];
    const seen = new Set();

    for (const row of rows) {
      if (!row.filePath || !selectionSet.has(row.filePath) || seen.has(row.filePath)) continue;
      seen.add(row.filePath);
      ordered.push(row.filePath);
    }

    return ordered;
  }

  function toggleGroupSelection(rows) {
    const filePaths = [...new Set(rows.map((row) => row.filePath).filter(Boolean))];
    const allSelected = filePaths.length > 0 && filePaths.every((filePath) => selections.has(filePath));

    for (const filePath of filePaths) {
      if (allSelected) selections.delete(filePath);
      else selections.add(filePath);
    }

    saveSelections(selections);
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

  function collectFilterValues(rows) {
    return Object.fromEntries(FIELDS.map(({ key }) => [key, collectUniqueValues(rows, key)]));
  }

  function collectUniqueValues(rows, field) {
    const values = new Set();
    for (const row of rows) {
      for (const value of row[field] || []) values.add(value);
    }
    return [...values].sort((left, right) => left.localeCompare(right));
  }

  function createFilterState() {
    const state = { search: "" };
    for (const { key } of FIELDS) state[key] = new Set();
    return state;
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
      row.slug,
      ...(row.class || []),
      ...(row.stage || []),
      ...(row.status || []),
    ]
      .map((value) => normalizeString(value).toLowerCase())
      .join(" ");

    return haystack.includes(search);
  }

  function parseLinkTarget(rawLink) {
    const [targetPart, aliasPart] = String(rawLink || "").split("|");
    const target = normalizeString(targetPart);
    const alias = normalizeString(aliasPart);
    const [targetWithoutBlock, blockRef = ""] = target.split("^");
    const [targetWithoutAnchor, anchor = ""] = targetWithoutBlock.split("#");

    return {
      alias,
      anchor: normalizeString(anchor),
      blockRef: normalizeString(blockRef),
      pageKey: stripMarkdownExtension(normalizePath(targetWithoutAnchor)),
    };
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

  function buildHref(base, anchor, blockRef) {
    const cleanBase = normalizeString(base);
    if (!cleanBase) return "";
    if (anchor) return `${cleanBase}#${anchor}`;
    if (blockRef) return `${cleanBase}^${blockRef}`;
    return cleanBase;
  }

  function styleFilterToken(button, active) {
    Object.assign(button.style, {
      cursor: "pointer",
      fontWeight: active ? "700" : "400",
      textDecoration: active ? "underline" : "none",
      padding: "0.05rem 0.35rem",
    });
  }

  function toValueList(value) {
    if (Array.isArray(value)) return value.map(normalizeString).filter(Boolean);
    const single = normalizeString(value);
    return single ? [single] : [];
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

  function isControlPath(value) {
    return normalizePath(value).startsWith("_control/");
  }

  function bindLifecycleHooks() {
    if (window[LIFECYCLE_KEY]) return;

    const invalidate = () => {
      window[SESSION_KEY] = null;
      window[COMMANDS_KEY] = null;
    };

    window[LIFECYCLE_KEY] = true;
    window.addEventListener("blur", invalidate);
    window.addEventListener("beforeunload", invalidate);
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") invalidate();
    });
  }
})();
