const ALPHABET = "abcdefghijklmnopqrstuvwxyz";

function randomAlpha(length = 6) {
  let output = "";
  for (let index = 0; index < length; index += 1) {
    const offset = Math.floor(Math.random() * ALPHABET.length);
    output += ALPHABET[offset];
  }
  return output;
}

function listMarkdownPaths() {
  try {
    if (typeof app !== "undefined" && app?.vault?.getMarkdownFiles) {
      return new Set(app.vault.getMarkdownFiles().map((file) => file.path));
    }
  } catch (_error) {
    // Ignore vault introspection failures and fall back to best-effort randomness.
  }
  return new Set();
}

function hasCollision(candidate, paths) {
  const fileName = `${candidate}.md`;
  for (const path of paths) {
    if (path === fileName || path.endsWith(`/${fileName}`)) {
      return true;
    }
  }
  return false;
}

module.exports.generate_slug = (domain) => {
  const normalized = typeof domain === "string" && domain.trim()
    ? domain.trim().toLowerCase()
    : "gbl";
  const existingPaths = listMarkdownPaths();

  for (let attempt = 0; attempt < 20; attempt += 1) {
    const length = attempt >= 10 ? 8 : 6;
    const candidate = `${normalized}.untitled.${randomAlpha(length)}`;
    if (!hasCollision(candidate, existingPaths)) {
      return candidate;
    }
  }

  return `${normalized}.untitled.${randomAlpha(8)}`;
};
