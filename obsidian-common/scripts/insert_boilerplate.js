/**
 * Insert a boilerplate at the cursor by reading from a reference note.
 *
 * Usage:
 * - Configure QuickAdd "Macro" with a "User Script" step pointing to this file.
 * - Provide (optionally) two "Arguments" to the step:
 *      arg0 = path to reference note (e.g. "Admin/Boilerplates.md")
 *      arg1 = boilerplate name (exact as shown after "BP:"), or leave blank to pick from a menu
 *
 * Reference note format:
 *   ## BP: Name
 *   (content until the next heading of same/higher level)
 *   - If a fenced block appears immediately under the BP heading, that block content is used.
 *   - Otherwise the entire section text is used.
 */
module.exports = async (params) => {
  const { app, quickAddApi, argv = [] } = params;

  // --- Read args or prompt for them
  const refPathArg = String(argv[0] || "").trim();
  const nameArg = String(argv[1] || "").trim();

  const getEditor = () => {
    const view = app.workspace.getActiveViewOfType(obsidian.MarkdownView);
    if (!view) throw new Error("No active Markdown editor.");
    return view.editor;
  };

  const readFile = async (path) => {
    const f = app.vault.getAbstractFileByPath(path);
    if (!f) throw new Error(`Reference note not found: ${path}`);
    if (!(f instanceof obsidian.TFile)) throw new Error(`Not a file: ${path}`);
    return app.vault.read(f);
  };

  // --- Parse the reference note into { name -> {depth, content} }
  const parseBoilerplates = (text) => {
    const lines = text.split(/\r?\n/);
    const sections = []; // { name, depth, startIdx, endIdx }
    const headingRE = /^(#{1,6})\s+BP:\s*(.+?)\s*$/;

    // First pass: find headings
    for (let i = 0; i < lines.length; i++) {
      const m = lines[i].match(headingRE);
      if (m) {
        sections.push({
          name: m[2],
          depth: m[1].length,
          startIdx: i + 1, // content starts after heading line
          endIdx: null,
        });
      }
    }

    // Second pass: set endIdx by looking ahead to next heading of same or higher depth
    for (let i = 0; i < sections.length; i++) {
      const { depth, startIdx } = sections[i];
      let end = lines.length;
      for (let j = startIdx; j < lines.length; j++) {
        const m2 = lines[j].match(/^(#{1,6})\s+/);
        if (m2 && m2[1].length <= depth) {
          end = j;
          break;
        }
      }
      sections[i].endIdx = end;
    }

    // Extract text for each, preferring first fenced block right after heading
    const map = new Map(); // name -> content
    const fenceRE = /^```(\w+)?\s*$/;

    for (const sec of sections) {
      const slice = lines.slice(sec.startIdx, sec.endIdx);

      // Trim leading blank lines
      while (slice.length && slice[0].trim() === "") slice.shift();
      // Prefer a fenced block at the top
      let content = slice.join("\n").trim();
      if (slice.length && fenceRE.test(slice[0])) {
        // find matching fence
        let i = 1;
        while (i < slice.length && !fenceRE.test(slice[i])) i++;
        if (i < slice.length && fenceRE.test(slice[i])) {
          content = slice.slice(1, i).join("\n").trim();
        }
      }
      map.set(sec.name, content);
    }
    return map;
  };

  // Simple placeholder expansion (extend as needed)
  const expandPlaceholders = (s) => {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    const yyyy = now.getFullYear();
    const mm = pad(now.getMonth() + 1);
    const dd = pad(now.getDate());
    const hh = pad(now.getHours());
    const mi = pad(now.getMinutes());

    return s
      .replaceAll("{{DATE}}", `${yyyy}-${mm}-${dd}`)
      .replaceAll("{{TIME}}", `${hh}:${mi}`);
  };

  try {
    // 1) Get reference path
    let refPath = refPathArg;
    if (!refPath) {
      // let user pick a file if not provided
      const files = app.vault.getMarkdownFiles().map((f) => f.path);
      refPath = await quickAddApi.suggester(files, files);
      if (!refPath) return; // user cancelled
    }

    // 2) Read + parse
    const text = await readFile(refPath);
    const bpMap = parseBoilerplates(text);
    if (bpMap.size === 0) {
      new obsidian.Notice("No boilerplates found (look for '## BP: Name' headings).");
      return;
    }

    // 3) Pick a boilerplate name
    let pickName = nameArg;
    if (!pickName || !bpMap.has(pickName)) {
      const names = [...bpMap.keys()].sort((a, b) => a.localeCompare(b));
      pickName = await quickAddApi.suggester(names, names);
      if (!pickName) return; // cancelled
    }

    const raw = bpMap.get(pickName);
    if (!raw) {
      new obsidian.Notice(`Boilerplate not found: ${pickName}`);
      return;
    }

    // 4) Insert at cursor
    const editor = getEditor();
    const cursor = editor.getCursor();
    const expanded = expandPlaceholders(raw);
    editor.replaceRange(expanded, cursor);

    new obsidian.Notice(`Inserted boilerplate: ${pickName}`);
  } catch (err) {
    console.error(err);
    new obsidian.Notice(`Boilerplate insert failed: ${err.message}`);
  }
};
 
