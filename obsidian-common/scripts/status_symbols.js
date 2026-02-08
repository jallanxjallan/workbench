/** status_symbols.js — Templater user script (Obsidian)
 *  Usage:
 *    - Hotkey → "Templater: Run user script" → choose this script
 *      (no arg) → prompts for mode, then symbol.
 *    - Or pass an arg: "clipboard" | "frontmatter" | "insert"
 *      via Templater’s “User Script Arguments”.
 *
 *  Example templates (optional):
 *    <%* await tp.user.status_symbols("clipboard") %>
 *    <%* await tp.user.status_symbols("frontmatter") %>
 *    <% tp.user.status_symbols("insert") %>
 */

module.exports = async (tp, mode = "ask") => {
  // —— Edit your status set here ——
  const symbols = [
    { key: "1", symbol: "🤖", name: "AI result" },
    { key: "2", symbol: "💬", name: "Prompt ready" },
    { key: "3", symbol: "🔧", name: "Needs structural edit" },
    { key: "4", symbol: "✨", name: "Polish pass needed" },
    { key: "5", symbol: "🔍", name: "Fact / verify" },
    { key: "6", symbol: "🛑", name: "Blocked / needs input" },
    { key: "7", symbol: "✅", name: "Ready / approved" },
    { key: "8", symbol: "🔳", name: "Placeholder" }
  ];
  // ————————————————

  const modes = [
    { id: "clipboard", label: "Copy to clipboard" },
    { id: "frontmatter", label: "Set YAML `status`" },
    { id: "insert", label: "Insert at cursor" }
  ];

  const pickMode = async () => {
    const labels = modes.map(m => m.label);
    const choice = await tp.system.suggester(labels, modes);
    return choice?.id;
  };

  const pickSymbol = async () => {
    const items = symbols.map(s => `${s.key}. ${s.symbol} — ${s.name}`);
    const choice = await tp.system.suggester(items, symbols);
    return choice?.symbol;
  };

  try {
    if (mode === "ask" || !["clipboard","frontmatter","insert"].includes(mode)) {
      const chosen = await pickMode();
      if (!chosen) {
        new Notice("Cancelled.");
        return;
      }
      mode = chosen;
    }

    const sel = await pickSymbol();
    if (!sel) {
      new Notice("No symbol selected.");
      return;
    }

    if (mode === "clipboard") {
      try {
        await navigator.clipboard.writeText(sel);
        new Notice(`Copied: ${sel}`);
      } catch (e) {
        // Fallback if clipboard blocked
        const editor = app.workspace.getActiveViewOfType(obsidian.MarkdownView)?.editor;
        if (editor) {
          const pos = editor.getCursor();
          editor.replaceRange(sel, pos);
          editor.setSelection(pos, { line: pos.line, ch: pos.ch + sel.length });
        }
        new Notice("Clipboard blocked by OS; inserted and selected instead.");
      }
      return;
    }

    if (mode === "frontmatter") {
      const file = tp.file.find_tfile(tp.file.path);
      if (!file) { new Notice("No active file."); return; }
      await app.fileManager.processFrontMatter(file, fm => { fm.status = sel; });
      new Notice(`YAML status set to ${sel}`);
      return;
    }

    if (mode === "insert") {
      return sel; // Templater inserts returned strings
    }
  } catch (err) {
    console.error(err);
    new Notice("Status symbol action failed (see console).");
  }
};
