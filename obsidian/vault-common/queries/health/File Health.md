```dataviewjs
(() => {
  const TEMPLATE_PATHS = {
    passage: "_common/templates/passage.md",
    image: "_common/templates/image.md",
  };

  const container = dv?.container ?? this?.container;
  if (!container) {
    if (typeof Notice === "function") new Notice("File Health: no render container.");
    return;
  }
  container.empty();

  const schemas = {};
  for (const [className, templatePath] of Object.entries(TEMPLATE_PATHS)) {
    const schema = buildTemplateSchema(templatePath);
    if (!schema) {
      container.createDiv({ text: `Could not load template schema: ${templatePath}` });
      return;
    }
    schemas[className] = schema;
  }

  const rows = [];
  for (const file of app.vault.getMarkdownFiles()) {
    const path = String(file.path || "");
    if (!path.startsWith("content/")) continue;

    const page = dv.page(path) || {};
    const frontmatterRaw = app.metadataCache.getFileCache(file)?.frontmatter || {};
    const frontmatter = sanitizeFrontmatter(frontmatterRaw);
    const classValue = normalizeValue(frontmatter.class).toLowerCase();

    const issues = {
      missing: [],
      incomplete: [],
      malformed: [],
    };

    if (!classValue) {
      issues.malformed.push("class");
    } else if (!schemas[classValue]) {
      issues.malformed.push(`class (${classValue})`);
    } else {
      const schema = schemas[classValue];
      for (const rule of schema.rules) {
        const valueAtPath = getPathValue(frontmatter, rule.segments);
        if (!valueAtPath.exists) {
          issues.missing.push(rule.path);
          continue;
        }

        const actual = valueAtPath.value;
        if (isMalformed(actual, rule.kind)) {
          issues.malformed.push(rule.path);
          continue;
        }

        if (isIncomplete(actual, rule.templateValue)) {
          issues.incomplete.push(rule.path);
        }
      }
    }

    const total =
      issues.missing.length +
      issues.incomplete.length +
      issues.malformed.length;
    if (total === 0) continue;

    rows.push({
      path,
      title: String(page?.title || file.basename || file.name || path),
      classValue: classValue || "—",
      missing: issues.missing,
      incomplete: issues.incomplete,
      malformed: issues.malformed,
      total,
    });
  }

  rows.sort((a, b) => b.total - a.total || a.title.localeCompare(b.title));

  const summary = container.createDiv();
  summary.setText(
    [
      `Template classes: ${Object.keys(TEMPLATE_PATHS).join(", ")}`,
      `content files with issues: ${rows.length}`,
    ].join(" | "),
  );

  if (rows.length === 0) {
    container.createDiv({
      text: "No content files are missing, incomplete, or malformed against the passage/image template fields.",
    });
    return;
  }

  dv.table(
    ["File", "Class", "Missing", "Incomplete", "Malformed", "Total"],
    rows.map((row) => [
      dv.fileLink(row.path),
      row.classValue,
      formatIssueList(row.missing),
      formatIssueList(row.incomplete),
      formatIssueList(row.malformed),
      row.total,
    ]),
  );

  function buildTemplateSchema(templatePath) {
    const templateFile = app.vault.getFileByPath(templatePath);
    if (!templateFile) return null;

    const cache = app.metadataCache.getFileCache(templateFile);
    const frontmatter = sanitizeFrontmatter(cache?.frontmatter || {});
    const rules = [];
    collectRules(frontmatter, [], rules);
    return { path: templatePath, rules };
  }

  function collectRules(node, prefix, rules) {
    for (const [key, value] of Object.entries(node || {})) {
      if (key === "position") continue;
      const segments = [...prefix, key];
      const path = segments.join(".");

      if (isPlainObject(value)) {
        rules.push({ path, segments, kind: "object", templateValue: value });
        collectRules(value, segments, rules);
        continue;
      }

      rules.push({
        path,
        segments,
        kind: inferKind(value),
        templateValue: value,
      });
    }
  }

  function inferKind(value) {
    if (Array.isArray(value)) return "array";
    if (isPlainObject(value)) return "object";
    if (typeof value === "boolean") return "boolean";
    if (typeof value === "number") return "number";
    return "scalar";
  }

  function getPathValue(root, segments) {
    let current = root;
    for (const segment of segments) {
      if (
        !current ||
        typeof current !== "object" ||
        Array.isArray(current) ||
        !Object.prototype.hasOwnProperty.call(current, segment)
      ) {
        return { exists: false };
      }
      current = current[segment];
    }
    return { exists: true, value: current };
  }

  function isMalformed(value, kind) {
    if (kind === "object") return !isPlainObject(value);
    if (kind === "array") return !Array.isArray(value);
    if (kind === "boolean") return typeof value !== "boolean";
    if (kind === "number") return typeof value !== "number";
    return isPlainObject(value) || Array.isArray(value);
  }

  function isIncomplete(actualValue, templateValue) {
    // Empty strings and placeholder tokens are considered incomplete.
    const templateText = normalizeValue(templateValue);
    const templateIsPlaceholder = /^__.+__$/.test(templateText);
    const templateRequiresText = templateText !== "" && !templateIsPlaceholder;

    if (templateIsPlaceholder) {
      if (actualValue == null) return true;
      if (typeof actualValue !== "string") return false;
      const actualText = actualValue.trim();
      return actualText === "" || /^__.+__$/.test(actualText);
    }

    if (templateRequiresText) {
      if (actualValue == null) return true;
      if (typeof actualValue !== "string") return false;
      const actualText = actualValue.trim();
      return actualText === "";
    }

    return false;
  }

  function formatIssueList(items) {
    if (!items || items.length === 0) return "—";
    const max = 6;
    if (items.length <= max) return items.join(", ");
    return `${items.slice(0, max).join(", ")} (+${items.length - max} more)`;
  }

  function sanitizeFrontmatter(node) {
    if (!isPlainObject(node)) return {};
    const out = {};
    for (const [key, value] of Object.entries(node)) {
      if (key === "position") continue;
      out[key] = isPlainObject(value) ? sanitizeFrontmatter(value) : value;
    }
    return out;
  }

  function isPlainObject(value) {
    return !!value && typeof value === "object" && !Array.isArray(value);
  }

  function normalizeValue(value) {
    if (value == null) return "";
    return String(value).trim();
  }
})();
```
