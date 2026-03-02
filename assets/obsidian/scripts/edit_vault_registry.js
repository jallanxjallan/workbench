// Obsidian macro: manually edit _vault_registry.json via prompts.
// Exposed through QuickAdd so it appears in the command palette.

module.exports = async function editVaultRegistry(params = {}) {
  const app = params.app || globalThis.app;
  const qa =
    params.quickAddApi ||
    params.quickAdd ||
    app?.plugins?.plugins?.quickadd?.api;

  if (!app || !app.vault || !app.workspace) {
    return fail("Obsidian app context not available.");
  }

  const registryPath = "_vault_registry.json";
  const vaultName = String(app.vault.getName?.() || "").trim() || "Vault";
  const defaultLabel = deriveLabel(vaultName);
  const defaultMnemonic = deriveMnemonic(vaultName);

  let existing = {};
  const currentFile = app.vault.getAbstractFileByPath(registryPath);
  if (currentFile && typeof currentFile.path === "string") {
    try {
      const raw = await app.vault.cachedRead(currentFile);
      const parsed = JSON.parse(String(raw || "{}"));
      if (parsed && typeof parsed === "object") existing = parsed;
    } catch (_) {
      // Ignore parse errors; user can overwrite with valid JSON through this macro.
    }
  }

  const label = await promptValue({
    qa,
    title: "Vault label",
    defaultValue: String(existing.label || defaultLabel),
  });
  if (label == null) return notice("Cancelled.");

  const mnemonic = await promptValue({
    qa,
    title: "Vault mnemonic",
    defaultValue: String(existing.mnemonic || defaultMnemonic),
  });
  if (mnemonic == null) return notice("Cancelled.");

  const payload = {
    ...existing,
    label: String(label).trim() || defaultLabel,
    mnemonic: String(mnemonic).trim() || defaultMnemonic,
  };

  // Optional loop for arbitrary extra fields.
  while (true) {
    const fieldNameInput = await promptValue({
      qa,
      title: "Add/edit field name (blank to finish)",
      defaultValue: "",
      useDefaultOnBlank: false,
    });
    if (fieldNameInput == null) return notice("Cancelled.");

    const fieldName = String(fieldNameInput).trim();
    if (!fieldName) break;

    const existingValue = Object.prototype.hasOwnProperty.call(payload, fieldName)
      ? payload[fieldName]
      : "";
    const valueInput = await promptValue({
      qa,
      title: `Value for '${fieldName}' (JSON or plain text)`,
      defaultValue: stringifyForPrompt(existingValue),
      useDefaultOnBlank: true,
    });
    if (valueInput == null) return notice("Cancelled.");

    payload[fieldName] = parseLooseValue(valueInput);
  }

  const content = `${JSON.stringify(payload, null, 2)}\n`;

  if (!currentFile) {
    await app.vault.create(registryPath, content);
  } else {
    await app.vault.modify(currentFile, content);
  }

  const opened = app.vault.getAbstractFileByPath(registryPath);
  if (opened && typeof opened.path === "string") {
    const leaf = app.workspace.getLeaf?.(true) || app.workspace.activeLeaf;
    if (leaf && typeof leaf.openFile === "function") {
      await leaf.openFile(opened);
    }
  }

  notice("Updated _vault_registry.json.");
};

async function promptValue({ qa, title, defaultValue, useDefaultOnBlank = true }) {
  const label = defaultValue
    ? `${title} (default: ${defaultValue})`
    : title;

  if (qa && typeof qa.inputPrompt === "function") {
    const value = await qa.inputPrompt(label);
    if (value == null) return null;
    const trimmed = String(value).trim();
    if (!trimmed) return useDefaultOnBlank ? defaultValue : "";
    return trimmed;
  }

  if (typeof window !== "undefined" && typeof window.prompt === "function") {
    const value = window.prompt(title, defaultValue);
    if (value == null) return null;
    const trimmed = String(value).trim();
    if (!trimmed) return useDefaultOnBlank ? defaultValue : "";
    return trimmed;
  }

  return defaultValue;
}

function stringifyForPrompt(value) {
  if (value === undefined) return "";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value);
  } catch (_) {
    return String(value);
  }
}

function parseLooseValue(input) {
  const text = String(input ?? "").trim();
  if (!text) return "";

  // Treat quoted strings, objects, arrays, booleans, null, and numbers as JSON.
  if (
    text.startsWith("{") ||
    text.startsWith("[") ||
    text.startsWith('"') ||
    text === "true" ||
    text === "false" ||
    text === "null" ||
    /^-?\d+(\.\d+)?$/.test(text)
  ) {
    try {
      return JSON.parse(text);
    } catch (_) {
      return text;
    }
  }

  return text;
}

function deriveLabel(vaultName) {
  const parts = String(vaultName || "")
    .trim()
    .split(/[\s_-]+/)
    .filter(Boolean);
  if (parts.length === 0) return "Vault";

  const tokens = [];
  for (const part of parts) {
    const pascal = part.match(/[A-Z]+(?=[A-Z][a-z]|$)|[A-Z][a-z0-9]*/g);
    if (pascal && pascal.length > 0) tokens.push(...pascal);
    else tokens.push(part);
  }

  return tokens
    .map((token) => {
      const t = String(token || "").trim();
      if (!t) return "";
      if (t.toUpperCase() === t) return t;
      return t.charAt(0).toUpperCase() + t.slice(1).toLowerCase();
    })
    .filter(Boolean)
    .join(" ");
}

function deriveMnemonic(vaultName) {
  const tokens = String(vaultName || "").match(
    /[A-Z]+(?=[A-Z][a-z]|$)|[A-Z][a-z0-9]*/g,
  );
  if (tokens && tokens.length > 1) {
    return tokens.map((token) => token.charAt(0).toLowerCase()).join("");
  }

  const letters = String(vaultName || "")
    .split("")
    .filter((char) => /[A-Za-z]/.test(char))
    .map((char) => char.toLowerCase());
  return letters.slice(0, 3).join("") || "vl";
}

function notice(message, timeout = 8000) {
  if (typeof Notice === "function") new Notice(message, timeout);
  console.log(message);
}

function fail(message) {
  const text = `Edit Vault Registry failed: ${message}`;
  if (typeof Notice === "function") new Notice(text, 10000);
  console.error(text);
}
