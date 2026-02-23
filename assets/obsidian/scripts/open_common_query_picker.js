// QuickAdd macro stub: query picker temporarily disabled.
// Open shared queries manually from _common/queries.

module.exports = async function openCommonQueryPicker(params = {}) {
  const app = params.app || globalThis.app;
  if (!app || !app.vault || !app.workspace) {
    return fail("Obsidian app context not available.");
  }

  notice("Open Common Query is stubbed. Open notes manually in _common/queries.", 8000);
};

function notice(message, timeout = 8000) {
  if (typeof Notice === "function") new Notice(message, timeout);
  console.log(message);
}

function fail(message) {
  const text = `Open Common Query failed: ${message}`;
  if (typeof Notice === "function") new Notice(text, 10000);
  console.error(text);
}
