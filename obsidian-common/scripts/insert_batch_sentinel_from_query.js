// Obsidian macro: Insert batch sentinel into selected files from an active query/view.
// Compatible entrypoint shape for QuickAdd and reusable from Templater/plugin code.
//
// Expected selection inputs can be passed via:
// - params.selectedFiles / params.selected / params.selection / params.selectedRows / params.selectedRefs
// - params.variables.selectedFiles / params.variables.selected / params.variables.selection
//   / params.variables.selectedRows / params.variables.selectedRefs
// Values may be arrays, newline-delimited strings, paths, wikilinks, or objects with `.path` / `.file.path`.

const LEGACY_SENTINEL_PREFIX = "<!-- asc:batch=";
const RAW_SENTINEL_PREFIX = "--- ASC BATCH:";

module.exports = async function insertBatchSentinelFromQuery(params = {}) {
  const app = params.app || globalThis.app;
  if (!app || !app.vault || !app.metadataCache) {
    fail("Obsidian app context not available.");
    return;
  }

  const notify = (message, timeout = 8000) => {
    if (typeof Notice === "function") new Notice(message, timeout);
    console.log(message);
  };

  try {
    const rawRefs = collectRawRefs(params, app);
    if (rawRefs.length === 0) {
      fail("No files were selected.");
      return;
    }

    const sourcePath =
      (params.sourcePath && String(params.sourcePath)) ||
      app.workspace?.getActiveFile?.()?.path ||
      "";

    const { files, unresolved } = resolveFilesFromRefs(app, rawRefs, sourcePath);
    if (files.length === 0) {
      fail("No files were selected.");
      return;
    }

    const sentinelInput = await promptForBatchLine(params, app);
    if (sentinelInput == null) {
      notify("Cancelled. No changes made.");
      return;
    }

    const sentinel = normalizeBatchSentinelLine(sentinelInput);
    if (!sentinel) {
      notify("Invalid batch slug. Expected it to start with 'batch-'. Aborting without changes.");
      return;
    }

    const confirmed = await confirmRun(params, sentinel, files);
    if (!confirmed) {
      notify("Cancelled. No changes made.");
      return;
    }

    // Safety: read and plan every change before writing anything.
    // This keeps mutation deterministic and lets us rollback on write errors.
    const plan = [];
    let skipped = 0;

    for (const file of files) {
      const original = await app.vault.read(file);

      // Sentinel logic: inspect ONLY line 1, never search deeper in the file.
      const firstLine = getFirstLine(original).replace(/^\uFEFF/, "");
      if (hasExistingBatchSentinel(firstLine, sentinel)) {
        skipped += 1;
        continue;
      }

      plan.push({
        file,
        original,
        updated: `${sentinel}\n\n${original}`,
      });
    }

    await writeWithRollback(app, plan);

    let summary = `Batch sentinel complete. Modified: ${plan.length}. Skipped: ${skipped}.`;
    if (unresolved > 0) summary += ` Unresolved: ${unresolved}.`;
    notify(summary, 10000);
  } catch (error) {
    fail(error?.message || String(error));
  }
};

function collectRawRefs(params, app) {
  const vars = params.variables || {};
  const selectedRefs = [];

  // Prefer explicit "selected" payloads if present.
  const selectedCandidates = [
    params.selectedFiles,
    params.selected,
    params.selection,
    params.selections,
    params.selectedItems,
    params.selectedRows,
    params.selectedRefs,
    params.selectedFile,
    vars.selectedFiles,
    vars.selected,
    vars.selection,
    vars.selections,
    vars.selectedItems,
    vars.selectedRows,
    vars.selectedRefs,
    vars.selectedFile,
  ];
  for (const candidate of selectedCandidates) flattenCandidate(candidate, selectedRefs);
  if (selectedRefs.length > 0) return selectedRefs;

  // Selection-only fallback: inspect the active view for highlighted/selected refs.
  return collectRefsFromActiveContext(app);
}

function collectRefsFromActiveContext(app) {
  const refs = [];
  const seen = new Set();
  const push = (value) => {
    const v = String(value || "").trim();
    if (!v || seen.has(v)) return;
    seen.add(v);
    refs.push(v);
  };

  // Selection fallback in editor: lets users run macro on a highlighted list of links/paths.
  const markdownViewClass = globalThis.MarkdownView;
  let activeView = app.workspace?.activeLeaf?.view;
  if (markdownViewClass && typeof app.workspace?.getActiveViewOfType === "function") {
    activeView = app.workspace.getActiveViewOfType(markdownViewClass) || activeView;
  }
  const selected = activeView?.editor?.getSelection?.();
  if (selected && selected.trim()) {
    const lines = selected.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    for (const line of lines) push(line);
  }

  const cursorRef = collectRefFromEditorCursor(activeView?.editor);
  if (cursorRef) push(cursorRef);

  const activeLeaf = app.workspace?.activeLeaf;
  const viewRoot =
    activeView?.containerEl ||
    activeView?.contentEl ||
    activeLeaf?.view?.containerEl ||
    activeLeaf?.view?.contentEl;
  if (!viewRoot || typeof viewRoot.querySelectorAll !== "function") return refs;

  // Selection fallback in rendered view (Dataview/search/etc).
  const domSelectionRefs = collectRefsFromDomSelection(viewRoot);
  for (const ref of domSelectionRefs) push(ref);

  // Primary for query UIs with tick-box selection (e.g., Draft Status results).
  const checkedBoxRefs = collectRefsFromCheckedBoxes(viewRoot);
  for (const ref of checkedBoxRefs) push(ref);

  const domCaretRef = collectRefFromDomCaret(viewRoot);
  if (domCaretRef) push(domCaretRef);

  // Focused/selected element handling: supports single-row keyboard/click selection.
  const focusedRef = collectFocusedInternalLinkRef(viewRoot);
  if (focusedRef) push(focusedRef);

  const selectedElementRefs = collectRefsFromSelectedElements(viewRoot);
  for (const ref of selectedElementRefs) push(ref);

  return refs;
}

function collectRefFromEditorCursor(editor) {
  if (!editor || typeof editor.getCursor !== "function" || typeof editor.getLine !== "function") return "";

  const cursor = editor.getCursor();
  if (!cursor || typeof cursor.line !== "number" || typeof cursor.ch !== "number") return "";

  const line = String(editor.getLine(cursor.line) || "");
  if (!line.trim()) return "";

  const tokens = extractLinkTokensFromText(line);
  if (tokens.length === 0) return "";

  const onCursor = tokens.find((token) => cursor.ch >= token.start && cursor.ch <= token.end);
  if (onCursor) return onCursor.raw;
  if (tokens.length === 1) return tokens[0].raw;

  return "";
}

function extractLinkTokensFromText(text) {
  const out = [];
  const addMatches = (regex) => {
    regex.lastIndex = 0;
    let match = regex.exec(text);
    while (match) {
      out.push({
        raw: match[0],
        start: match.index,
        end: match.index + match[0].length,
      });
      match = regex.exec(text);
    }
  };

  addMatches(/!?\[\[[^[\]]+\]\]/g);
  addMatches(/\[[^\]]*]\(([^)]+)\)/g);

  out.sort((a, b) => a.start - b.start);
  return out;
}

function collectRefsFromDomSelection(viewRoot) {
  if (
    !viewRoot ||
    typeof window === "undefined" ||
    typeof window.getSelection !== "function"
  ) {
    return [];
  }

  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0 || selection.isCollapsed) return [];

  const refs = [];
  const seen = new Set();
  const push = (value) => {
    const v = String(value || "").trim();
    if (!v || seen.has(v)) return;
    seen.add(v);
    refs.push(v);
  };

  for (let i = 0; i < selection.rangeCount; i += 1) {
    const range = selection.getRangeAt(i);
    const container =
      range.commonAncestorContainer?.nodeType === 1
        ? range.commonAncestorContainer
        : range.commonAncestorContainer?.parentElement;
    if (!container || !viewRoot.contains(container)) continue;

    const fragment = range.cloneContents?.();
    if (fragment && typeof fragment.querySelectorAll === "function") {
      const links = fragment.querySelectorAll("a.internal-link");
      for (const link of links) {
        const href =
          link?.dataset?.href ||
          link?.getAttribute?.("data-href") ||
          link?.getAttribute?.("href");
        if (!href) continue;
        push(decodeAndStripHash(href));
      }
    }

    const text = String(range.toString() || "").trim();
    if (!text) continue;
    const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    for (const line of lines) push(line);
  }

  return refs;
}

function collectRefsFromCheckedBoxes(viewRoot) {
  if (!viewRoot || typeof viewRoot.querySelectorAll !== "function") return [];

  const refs = [];
  const seen = new Set();
  const push = (value) => {
    const v = String(value || "").trim();
    if (!v || seen.has(v)) return;
    seen.add(v);
    refs.push(v);
  };

  // Restrict scanning to common rendered-query containers plus known result wrapper.
  const containers = [];
  const seenContainers = new Set();
  const containerSelectors = [
    ".status-results",
    ".dataview",
    ".block-language-dataview",
    ".block-language-dataviewjs",
    ".internal-query",
    ".search-result-container",
  ];

  for (const selector of containerSelectors) {
    const nodes = viewRoot.querySelectorAll(selector);
    for (const node of nodes) {
      if (seenContainers.has(node)) continue;
      seenContainers.add(node);
      containers.push(node);
    }
  }
  if (containers.length === 0) containers.push(viewRoot);

  for (const container of containers) {
    const checked = container.querySelectorAll("input[type='checkbox']:checked");
    for (const box of checked) {
      const ref = resolveRefFromCheckedBox(box, viewRoot);
      if (ref) push(ref);
    }
  }

  return refs;
}

function resolveRefFromCheckedBox(box, viewRoot) {
  if (!box || !viewRoot || !viewRoot.contains(box)) return "";

  // Fast path: link adjacent to checkbox in same row.
  const siblingLink =
    box.nextElementSibling?.matches?.("a.internal-link")
      ? box.nextElementSibling
      : null;
  if (siblingLink) {
    const href = getInternalLinkHref(siblingLink);
    if (href) return decodeAndStripHash(href);
  }

  const scopes = [
    box.closest?.("li"),
    box.closest?.("tr"),
    box.closest?.(".dataview-result-list-li"),
    box.closest?.(".dataview-result-list-item"),
    box.closest?.(".search-result-file-match"),
    box.closest?.(".search-result"),
    box.parentElement,
  ].filter(Boolean);

  for (const scope of scopes) {
    if (!viewRoot.contains(scope) || typeof scope.querySelectorAll !== "function") continue;
    const links = scope.querySelectorAll("a.internal-link");
    const best = pickBestInternalLink(links);
    if (!best) continue;
    const href = getInternalLinkHref(best);
    if (href) return decodeAndStripHash(href);
  }

  return "";
}

function collectRefFromDomCaret(viewRoot) {
  if (
    !viewRoot ||
    typeof window === "undefined" ||
    typeof window.getSelection !== "function"
  ) {
    return "";
  }

  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0 || !selection.isCollapsed) return "";

  const range = selection.getRangeAt(0);
  const node =
    range.startContainer?.nodeType === 1
      ? range.startContainer
      : range.startContainer?.parentElement;
  if (!node || !viewRoot.contains(node)) return "";

  const nearNodeRef = resolveInternalLinkNearNode(node, viewRoot);
  if (nearNodeRef) return nearNodeRef;

  // Some views place the collapsed range on a wrapper node; probe the caret point.
  if (typeof document === "undefined" || typeof document.elementFromPoint !== "function") return "";
  const rect = range.getBoundingClientRect?.();
  if (!rect) return "";

  const x = Math.floor(rect.left + rect.width / 2);
  const y = Math.floor(rect.top + rect.height / 2);
  const pointNode = document.elementFromPoint(x, y);
  if (!pointNode || !viewRoot.contains(pointNode)) return "";

  const nearPointRef = resolveInternalLinkNearNode(pointNode, viewRoot);
  if (nearPointRef) return nearPointRef;

  return "";
}

function collectFocusedInternalLinkRef(viewRoot) {
  if (!viewRoot || typeof document === "undefined") return "";
  const active = document.activeElement;
  if (!active || !viewRoot.contains(active)) return "";

  const nearActiveRef = resolveInternalLinkNearNode(active, viewRoot);
  if (nearActiveRef) return nearActiveRef;

  // Support composite widgets that track active descendants by id.
  const activeDescendantId = active.getAttribute?.("aria-activedescendant");
  if (activeDescendantId && typeof document.getElementById === "function") {
    const desc = document.getElementById(activeDescendantId);
    if (desc && viewRoot.contains(desc)) {
      const nearDescRef = resolveInternalLinkNearNode(desc, viewRoot);
      if (nearDescRef) return nearDescRef;
    }
  }

  return "";
}

function resolveInternalLinkNearNode(node, viewRoot) {
  if (!node || !viewRoot || !viewRoot.contains(node)) return "";

  const link =
    node.matches?.("a.internal-link")
      ? node
      : node.closest?.("a.internal-link");
  if (link) {
    const href = getInternalLinkHref(link);
    return href ? decodeAndStripHash(href) : "";
  }

  // Try row-like scopes first (query list row, table row, search row).
  const scopes = [
    node.closest?.(".dataview-result-list-li"),
    node.closest?.(".dataview-result-list-item"),
    node.closest?.("tr"),
    node.closest?.("li"),
    node.closest?.(".search-result"),
    node.closest?.(".search-result-file-match"),
    node.closest?.("p"),
  ].filter(Boolean);

  for (const scope of scopes) {
    if (!viewRoot.contains(scope) || typeof scope.querySelectorAll !== "function") continue;
    const links = scope.querySelectorAll("a.internal-link");
    const best = pickBestInternalLink(links);
    if (!best) continue;
    const href = getInternalLinkHref(best);
    if (href) return decodeAndStripHash(href);
  }

  return "";
}

function pickBestInternalLink(links) {
  if (!links || links.length === 0) return null;
  if (links.length === 1) return links[0];

  // Prefer file links over heading/block links when multiple links are present.
  for (const link of links) {
    const href = getInternalLinkHref(link);
    if (href && !href.includes("#")) return link;
  }

  return links[0];
}

function collectRefsFromSelectedElements(viewRoot) {
  if (!viewRoot || typeof viewRoot.querySelectorAll !== "function") return [];

  const selectors = [
    "a.internal-link.is-selected",
    ".is-selected a.internal-link",
    ".selected a.internal-link",
    "tr[aria-selected='true'] a.internal-link",
    "a.internal-link[aria-selected='true']",
  ];

  const refs = [];
  const seen = new Set();
  const push = (value) => {
    const v = String(value || "").trim();
    if (!v || seen.has(v)) return;
    seen.add(v);
    refs.push(v);
  };

  for (const selector of selectors) {
    const links = viewRoot.querySelectorAll(selector);
    for (const link of links) {
      const href = getInternalLinkHref(link);
      if (!href) continue;
      push(decodeAndStripHash(href));
    }
  }

  return refs;
}

function getInternalLinkHref(link) {
  return (
    link?.dataset?.href ||
    link?.getAttribute?.("data-href") ||
    link?.getAttribute?.("href") ||
    ""
  );
}

function decodeAndStripHash(href) {
  const raw = String(href || "").trim();
  if (!raw) return raw;

  const withoutHash = raw.split("#")[0];
  try {
    return decodeURIComponent(withoutHash);
  } catch (_) {
    return withoutHash;
  }
}

function flattenCandidate(input, out) {
  if (input == null) return;

  if (Array.isArray(input)) {
    for (const item of input) flattenCandidate(item, out);
    return;
  }

  if (typeof input === "string") {
    const text = input.trim();
    if (!text) return;

    if (text.startsWith("[") && text.endsWith("]")) {
      try {
        const parsed = JSON.parse(text);
        flattenCandidate(parsed, out);
        return;
      } catch (_) {
        // fall through to line splitting
      }
    }

    for (const line of text.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (trimmed) out.push(trimmed);
    }
    return;
  }

  if (typeof input === "object") {
    if (typeof input.path === "string") {
      out.push(input.path);
      return;
    }
    if (input.file && typeof input.file.path === "string") {
      out.push(input.file.path);
      return;
    }
    if ("value" in input) {
      flattenCandidate(input.value, out);
      return;
    }
    if (Array.isArray(input.values)) {
      flattenCandidate(input.values, out);
      return;
    }

    const asText = String(input).trim();
    if (asText && asText !== "[object Object]") out.push(asText);
  }
}

function resolveFilesFromRefs(app, rawRefs, sourcePath) {
  const files = [];
  const seen = new Set();
  let unresolved = 0;

  for (const rawRef of rawRefs) {
    const resolved = resolveSingleRef(app, rawRef, sourcePath);
    if (!resolved) {
      unresolved += 1;
      continue;
    }
    if (seen.has(resolved.path)) continue;
    seen.add(resolved.path);
    files.push(resolved);
  }

  return { files, unresolved };
}

function resolveSingleRef(app, rawRef, sourcePath) {
  const parsed = parseRef(String(rawRef || ""));
  if (!parsed) return null;

  if (parsed.kind === "wikilink") {
    return resolveLinkPath(app, parsed.target, sourcePath);
  }
  return resolveVaultPath(app, parsed.target, sourcePath);
}

function parseRef(raw) {
  const trimmed = raw.trim();
  if (!trimmed) return null;

  const withoutBullet = trimmed
    .replace(/^[-*+]\s+/, "")
    .replace(/^\d+\.\s+/, "")
    .trim();
  const unquoted = stripWrappingQuotes(withoutBullet);
  if (!unquoted) return null;

  const wikiMatch = unquoted.match(/!?\[\[([^[\]]+)\]\]/);
  if (wikiMatch) {
    return { kind: "wikilink", target: normalizeWikilinkTarget(wikiMatch[1]) };
  }

  const mdLinkMatch = unquoted.match(/\[[^\]]*]\(([^)]+)\)/);
  if (mdLinkMatch) {
    return { kind: "path", target: stripWrappingQuotes(mdLinkMatch[1].trim()) };
  }

  return { kind: "path", target: unquoted };
}

function stripWrappingQuotes(text) {
  const s = text.trim();
  if (
    (s.startsWith('"') && s.endsWith('"')) ||
    (s.startsWith("'") && s.endsWith("'"))
  ) {
    return s.slice(1, -1).trim();
  }
  return s;
}

function normalizeWikilinkTarget(target) {
  // Keep linkpath only (drop alias/header/block refs), since file resolution uses path component.
  const noAlias = target.split("|")[0];
  const noHeading = noAlias.split("#")[0];
  const noBlock = noHeading.split("^")[0];
  return noBlock.trim();
}

function resolveLinkPath(app, linkPath, sourcePath) {
  if (!linkPath) return null;
  const file = app.metadataCache.getFirstLinkpathDest(linkPath, sourcePath || "");
  if (isMarkdownFile(file)) return file;
  return null;
}

function resolveVaultPath(app, rawPath, sourcePath) {
  if (!rawPath) return null;

  const normalize = app.vault.adapter?.normalizePath
    ? (p) => app.vault.adapter.normalizePath(p)
    : (p) => String(p).replace(/\\/g, "/");

  const base = stripLeadingSlash(rawPath.trim());
  const direct = getMarkdownByPath(app, normalize(base));
  if (direct) return direct;

  if (!/\.md$/i.test(base)) {
    const withMd = getMarkdownByPath(app, normalize(`${base}.md`));
    if (withMd) return withMd;
  }

  // Fallback for relative/internal-style paths.
  const linkFallback = app.metadataCache.getFirstLinkpathDest(base, sourcePath || "");
  if (isMarkdownFile(linkFallback)) return linkFallback;

  return null;
}

function stripLeadingSlash(path) {
  return String(path).replace(/^\/+/, "");
}

function getMarkdownByPath(app, path) {
  const file = app.vault.getAbstractFileByPath(path);
  if (isMarkdownFile(file)) return file;
  return null;
}

function isMarkdownFile(file) {
  return !!file && typeof file.path === "string" && file.extension === "md";
}

function getFirstLine(text) {
  const newlineIndex = text.indexOf("\n");
  if (newlineIndex < 0) return text;
  return text.slice(0, newlineIndex);
}

async function promptForBatchLine(params, app) {
  const qa = params.quickAddApi || params.quickAddAPI || params.api;
  if (qa && typeof qa.inputPrompt === "function") {
    return qa.inputPrompt("Batch slug");
  }

  if (app?.plugins?.plugins?.quickadd?.api?.inputPrompt) {
    return app.plugins.plugins.quickadd.api.inputPrompt("Batch slug");
  }

  if (typeof window !== "undefined" && typeof window.prompt === "function") {
    return window.prompt("Enter batch slug (without wrappers)");
  }

  throw new Error("No prompt API available to request batch slug.");
}

function normalizeBatchSentinelLine(input) {
  const raw = String(input || "").trim();
  if (!raw) return "";

  const wrapped = raw.match(/^---\s*ASC\s+BATCH:\s*(.*?)\s*---$/i);
  if (wrapped) {
    const slug = wrapped[1].trim();
    if (!slug || !isValidBatchSlug(slug)) return "";
    return `--- ASC BATCH: ${slug} ---`;
  }

  const prefixed = raw.match(/^---\s*ASC\s+BATCH:\s*(.*)$/i);
  if (prefixed) {
    const slug = prefixed[1].replace(/\s*---\s*$/, "").trim();
    if (!slug || !isValidBatchSlug(slug)) return "";
    return `--- ASC BATCH: ${slug} ---`;
  }

  const legacy = raw.match(/^<!--\s*asc:batch=(.*?)\s*-->$/i);
  if (legacy) {
    const slug = legacy[1].trim();
    if (!slug || !isValidBatchSlug(slug)) return "";
    return `--- ASC BATCH: ${slug} ---`;
  }

  if (!isValidBatchSlug(raw)) return "";
  return `--- ASC BATCH: ${raw} ---`;
}

function isValidBatchSlug(slug) {
  const value = String(slug || "").trim();
  // Accept base slug and optional suffix segments, e.g.:
  // batch-11feb-1219
  // batch-11feb-1219-foo-bar
  return value.startsWith("batch-") && value.length > "batch-".length;
}

async function confirmRun(params, sentinel, files) {
  const qa = params.quickAddApi || params.quickAddAPI || params.api;
  const message = buildConfirmationMessage(sentinel, files);

  if (qa && typeof qa.yesNoPrompt === "function") {
    return qa.yesNoPrompt("Confirm Batch Sentinel", message);
  }

  if (typeof window !== "undefined" && typeof window.confirm === "function") {
    return window.confirm(message);
  }

  throw new Error("No confirmation API available.");
}

function buildConfirmationMessage(sentinel, files) {
  const list = Array.isArray(files) ? files : [];
  if (list.length === 0) return "No files were selected.";

  const previewCount = 5;
  const previewLines = list
    .slice(0, previewCount)
    .map((file) => `- ${getFileTitle(file)}`)
    .join("\n");

  let message = `Inject this batch sentinel?\n\n${sentinel}\n\nSelected files (${list.length}):\n${previewLines}`;
  if (list.length > previewCount) {
    message += `\n...and ${list.length - previewCount} more file(s).`;
  }

  return message;
}

function getFileTitle(file) {
  if (file && typeof file.basename === "string" && file.basename.trim()) {
    return file.basename.trim();
  }

  const path = String(file?.path || "").trim();
  if (!path) return "(untitled)";

  const leaf = path.split("/").pop() || path;
  return leaf.replace(/\.md$/i, "");
}

async function writeWithRollback(app, plan) {
  if (plan.length === 0) return;

  const applied = [];
  try {
    for (const item of plan) {
      await app.vault.modify(item.file, item.updated);
      applied.push(item);
    }
  } catch (writeError) {
    let rollbackFailures = 0;
    for (let i = applied.length - 1; i >= 0; i -= 1) {
      try {
        await app.vault.modify(applied[i].file, applied[i].original);
      } catch (_) {
        rollbackFailures += 1;
      }
    }

    if (rollbackFailures > 0) {
      throw new Error(
        `Write failed and rollback was incomplete (${rollbackFailures} file(s) could not be restored): ${
          writeError?.message || String(writeError)
        }`,
      );
    }

    throw new Error(`Write failed and all prior changes were rolled back: ${writeError?.message || String(writeError)}`);
  }
}

function fail(message) {
  const text = `Batch sentinel failed: ${message}`;
  if (typeof Notice === "function") new Notice(text, 10000);
  console.error(text);
}

function hasExistingBatchSentinel(firstLine, currentSentinelLine) {
  if (!firstLine) return false;

  // Safety: treat both legacy and raw batch headers as sentinel-occupied line 1.
  if (firstLine.startsWith(LEGACY_SENTINEL_PREFIX)) return true;
  if (firstLine.startsWith(RAW_SENTINEL_PREFIX)) return true;

  // Also skip if line 1 already exactly matches the currently requested raw line.
  return firstLine === currentSentinelLine;
}
