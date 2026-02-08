// qa_sysmessage_slug.js — set file_name, archetype, slug (kebab-case)
module.exports = async (params) => {
  const { quickAddApi, variables } = params;

  const values = await quickAddApi.requestInputs([
    { id: "file_name", label: "File name", type: "text", placeholder: "Polish text" },
    { id: "archetype", label: "Archetype", type: "dropdown",
      options: ["commissioned","translation","web","memoir","generic"] }
  ]);

  const toKebab = (s) =>
    String(s || "")
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .replace(/-{2,}/g, "-");

  const fileName = values.file_name || "untitled";
  const archetype = values.archetype || "generic";
  const slug = `${toKebab(archetype)}-${toKebab(fileName)}`;

  // expose for {{VALUE:*}} tokens in the template
  variables.file_name = fileName;
  variables.archetype = archetype;
  variables.slug = slug;

  return ""; // injects nothing into the template; just sets variables
};

