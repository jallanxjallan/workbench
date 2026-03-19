const path = require("path");

module.exports = async function submitBatch(params = {}) {
  const helper = loadHelper(params);

  try {
    return await helper.runBatchMacro(params, "submit");
  } catch (error) {
    const detail = error?.message || String(error);
    if (typeof Notice === "function") new Notice(detail, 10000);
    console.error(`Submit Batch failed: ${detail}`);
    return null;
  }
};

function loadHelper(params = {}) {
  const app = params.app || globalThis.app || (typeof window !== "undefined" ? window.app : null);
  const adapter = app?.vault?.adapter;
  const basePath =
    (adapter && typeof adapter.getBasePath === "function" && adapter.getBasePath()) ||
    adapter?.basePath;

  if (!basePath) {
    throw new Error("vault base path is unavailable");
  }

  return require(path.join(String(basePath), "_control", "macros", "_order_safe_batch.js"));
}
