// QuickAdd Macro: Create Dynamic Note (Folder + Template pickers, slug prefix)
// Fixed: uses f.type instead of instanceof, defaults template folder to common/templates.

module.exports = async (params) => {
  const { app, Notice } = globalThis;
  const qa = params?.quickAddApi;
  if (!qa) {
    new Notice("QuickAdd API not available.", 6000);
    return;
  }

  // ---------- SETTINGS ----------
  const DEFAULT_TEMPLATE_FOLDER = "common/templates";
  const DEBUG = false; // set true to show counts/paths in Notices
  const EXCLUDE_FOLDER_BASENAMES = new Set([".obsidian", "common", "index"]);
  const OPTIONAL_INIT_MACRO_NAME = "Init System Message Metadata";
  // ------------------------------

  // Resolve template folder (Templater setting or default)
  const templater = app.plugins.plugins["templater-obsidian"];
  let templateFolderPath = (templater?.settings?.template_folder || "").trim();
  if (!templateFolderPath) templateFolderPath = DEFAULT_TEMPLATE_FOLDER;
  // normalize: remove leading/trailing slashes
  templateFolderPath = templateFolderPath.replace(/^\/+/, "").replace(/\/+$/, "");

  const all = app.vault.getAllLoadedFiles();

  // Validate the template folder exists
  const tplFolder = app.vault.getAbstractFileByPath(templateFolderPath);
  if (!tplFolder || tplFolder.type !== "folder") {
    new Notice(`Template folder not found or not a folder: ${templateFolderPath}`, 7000);
    if (DEBUG) {
      const folderList = all.filter(f => f.type === "folder").slice(0, 15).map(f => f.path).join("
");
      new Notice(`Some existing folders:
${folderList}`, 9000);
    }
    return;
  }

  // Collect markdown templates under the template folder (recursive)
  const templates = all
    .filter((f) => f.type === "file" && f.extension === "md" && (f.path === `${templateFolderPath}/${f.name}` || f.path.startsWith(templateFolderPath + "/")))
    .map((f) => ({ path: f.path, label: f.path.slice(templateFolderPath.length + 1) }));

  if (!templates.length) {
    if (DEBUG) {
      const filesInTpl = all.filter(f => f.type === "file" && f.path.startsWith(templateFolderPath + "/")).map(f => f.path).join("
");
      new Notice(`No .md files found under ${templateFolderPath}. Seen files:
${filesInTpl || "<none>"}`, 9000);
    }
    new Notice(`No templates found under: ${templateFolderPath}`, 6000);
    return;
  }

  // Collect candidate folders
  const folders = all
    .filter((f) => f.type === "folder")
    .filter((f) => !EXCLUDE_FOLDER_BASENAMES.has((f.name || "").toLowerCase()))
    .map((f) => ({ path: f.path, label: f.path }));

  if (!folders.length) {
    new Notice("No folders available for selection.", 6000);
    return;
  }

  const sanitize = (s) => String(s).replace(/[\\/:"*?<>|]+/g, "").trim();
  const toKebab = (s) =>
    String(s || "")
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .replace(/-{2,}/g, "-");

  // 1) Pick folder
  const pickedFolder = await qa.suggester(folders.map((f) => f.label), folders);
  if (!pickedFolder) return;

  // 2) Pick template
  const pickedTpl = await qa.suggester(templates.map((t) => t.label), templates);
  if (!pickedTpl) return;

  // 3) Enter title
  const title = await qa.inputPrompt("New note title");
  if (!title) return;

  const folder = app.vault.getAbstractFileByPath(pickedFolder.path);
  const tplFile = app.vault.getAbstractFileByPath(pickedTpl.path);

  if (!folder) {
    new Notice(`Target folder not found: ${pickedFolder.path}`, 6000);
    return;
  }
  if (!tplFile) {
    new Notice(`Template not found: ${pickedTpl.path}`, 6000);
    return;
  }

  const baseName = sanitize(title);
  let filePath = `${folder.path}/${baseName}.md`;
  let suffix = 2;
  while (app.vault.getAbstractFileByPath(filePath)) {
    filePath = `${folder.path}/${baseName} ${suffix}.md`;
    suffix++;
  }

  const file = await app.vault.create(filePath, "");
  const tpl = await app.vault.read(tplFile);
  await app.vault.modify(file, tpl);

  await app.workspace.getLeaf(true).openFile(file);
  await app.commands.executeCommandById("templater-obsidian:replace-in-file");

  try {
    const quickadd = app.plugins.plugins.quickadd;
    if (quickadd?.api && OPTIONAL_INIT_MACRO_NAME) {
      await quickadd.api.runMacro(OPTIONAL_INIT_MACRO_NAME);
    }
  } catch (e) {
    // ignore
  }

  const parentName = folder.name || folder.path.split("/").pop();
  const slug = `${toKebab(parentName)}-${toKebab(baseName)}`;

  await app.fileManager.processFrontMatter(file, (fm) => {
    fm.slug = slug;
    fm.updated = new Date().toISOString();
  });

  new Notice(`Created: ${file.path}\nTemplate: ${pickedTpl.label}\nSlug: ${slug}`, 5000);
};
