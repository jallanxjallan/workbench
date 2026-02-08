// Obsidian macro: Insert batch sentinel into files provided by an active query.
// Compatible entrypoint shape for QuickAdd and reusable from Templater/plugin code.
//
// Expected query inputs can be passed via:
// - params.fileRefs / params.queryResults / params.files
// - params.variables.fileRefs / params.variables.queryResults / params.variables.files
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
      notify("No files found from query input, active query render, or selection. Aborting.");
      return;
    }

    const sourcePath =
      (params.sourcePath && String(params.sourcePath)) ||
      app.workspace?.getActiveFile?.()?.path ||
      "";

    const { files, unresolved } = resolveFilesFromRefs(app, rawRefs, sourcePath);
    if (files.length === 0) {
      notify("No query references could be resolved to markdown files. Aborting.");
      return;
    }

    const sentinelInput = await promptForBatchLine(params, app);
    if (sentinelInput == null) {
      notify("Cancelled. No changes made.");
      return;
    }

    const sentinel = String(sentinelInput).trim();
    if (!sentinel) {
      notify("Empty batch sentinel line. Aborting without changes.");
      return;
    }

    const confirmed = await confirmRun(params, sentinel, files.length);
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
  const out = [];

  const candidates = [
    params.fileRefs,
    params.queryResults,
    params.files,
    params.references,
    vars.fileRefs,
    vars.queryResults,
    vars.files,
    vars.references,
    vars.selectedFiles,
    vars.selected,
    vars.queryOutput,
  ];

  for (const candidate of candidates) {
    flattenCandidate(candidate, out);
  }

  // Fallback: if no explicit query payload was passed, inspect the active query view
  // and selected text to support hotkey-triggered execution.
  if (out.length === 0) {
    const fallbackRefs = collectRefsFromActiveContext(app);
    for (const ref of fallbackRefs) out.push(ref);
  }

  return out;
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

  // Selection fallback: lets users run macro on a highlighted list of links/paths.
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

  // Active query fallback: collect links from rendered query containers only.
  const activeLeaf = app.workspace?.activeLeaf;
  const viewRoot = activeLeaf?.view?.containerEl || activeLeaf?.view?.contentEl;
  if (!viewRoot || typeof viewRoot.querySelectorAll !== "function") return refs;

  const queryContainerSelectors = [
    ".dataview",
    ".block-language-dataview",
    ".block-language-dataviewjs",
    ".internal-query",
    ".search-result-container",
  ];

  const anchors = new Set();
  for (const selector of queryContainerSelectors) {
    const containers = viewRoot.querySelectorAll(selector);
    for (const container of containers) {
      const links = container.querySelectorAll("a.internal-link");
      for (const link of links) anchors.add(link);
    }
  }

  for (const anchor of anchors) {
    const href = anchor?.dataset?.href || anchor?.getAttribute?.("data-href") || anchor?.getAttribute?.("href");
    if (!href) continue;
    push(decodeAndStripHash(href));
  }

  return refs;
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
    return qa.inputPrompt("Batch sentinel line");
  }

  if (app?.plugins?.plugins?.quickadd?.api?.inputPrompt) {
    return app.plugins.plugins.quickadd.api.inputPrompt("Batch sentinel line");
  }

  if (typeof window !== "undefined" && typeof window.prompt === "function") {
    return window.prompt("Enter full batch sentinel line");
  }

  throw new Error("No prompt API available to request batch slug.");
}

async function confirmRun(params, sentinel, count) {
  const qa = params.quickAddApi || params.quickAddAPI || params.api;
  const message = `Insert sentinel into ${count} file(s)?\n\n${sentinel}`;

  if (qa && typeof qa.yesNoPrompt === "function") {
    return qa.yesNoPrompt("Confirm Batch Sentinel", message);
  }

  if (typeof window !== "undefined" && typeof window.confirm === "function") {
    return window.confirm(message);
  }

  throw new Error("No confirmation API available.");
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
