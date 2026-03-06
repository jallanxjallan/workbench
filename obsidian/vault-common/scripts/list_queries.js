module.exports = async function listQueries(params = {}) {
  const app = params.app || globalThis.app;
  if (!app || !app.vault || !app.workspace) {
    return notice("Obsidian context not available.");
  }

  const ROOT = "_common/queries";
  const INDEX = `${ROOT}/Common Query Index.md`;
  const folder = app.vault.getAbstractFileByPath(ROOT);

  if (!folder || !Array.isArray(folder.children)) {
    return notice(`Folder not found: ${ROOT}`);
  }

  const sections = {};
  collectQueryFiles(folder, ROOT, INDEX).forEach((file) => {
    const relative = file.path.replace(`${ROOT}/`, "");
    const parts = relative.split("/");
    const group = parts.length > 1 ? parts[0] : "General";
    if (!sections[group]) {
      sections[group] = [];
    }
    sections[group].push(file);
  });

  const lines = ["# Common Query Index", ""];
  const groups = Object.keys(sections).sort((a, b) => a.localeCompare(b));
  groups.forEach((group) => {
    lines.push(`## ${group}`, "");
    sections[group]
      .sort((a, b) => {
        const byName = a.basename.localeCompare(b.basename);
        if (byName !== 0) {
          return byName;
        }
        return a.path.localeCompare(b.path);
      })
      .forEach((file) => {
        const target = file.path.replace(/\.md$/i, "");
        lines.push(`- [[${target}|${file.basename}]]`);
      });
    lines.push("");
  });

  const content = lines.join("\n");
  const existing = app.vault.getAbstractFileByPath(INDEX);

  let indexFile;
  if (!existing) {
    indexFile = await app.vault.create(INDEX, content);
  } else {
    if (existing.extension !== "md") {
      return notice(`Index path is not a markdown file: ${INDEX}`);
    }

    const current = await app.vault.read(existing);
    if (current !== content) {
      await app.vault.modify(existing, content);
    }
    indexFile = existing;
  }

  const leaf = app.workspace.getLeaf?.(true) || app.workspace.activeLeaf;
  if (!leaf || typeof leaf.openFile !== "function") {
    return notice("No workspace leaf available.");
  }
  await leaf.openFile(indexFile);
  notice("Opened Common Query Index");
};

function collectQueryFiles(folder, rootPath, indexPath) {
  const files = [];
  const stack = [...folder.children];

  while (stack.length > 0) {
    const current = stack.pop();
    if (!current) {
      continue;
    }

    if (Array.isArray(current.children)) {
      current.children.forEach((child) => stack.push(child));
      continue;
    }

    if (current.extension !== "md") {
      continue;
    }
    if (current.path === indexPath) {
      continue;
    }
    if (!current.path.startsWith(`${rootPath}/`)) {
      continue;
    }

    files.push(current);
  }

  return files;
}

function notice(msg) {
  if (typeof Notice !== "undefined") {
    new Notice(msg);
  }
  console.log(msg);
}
