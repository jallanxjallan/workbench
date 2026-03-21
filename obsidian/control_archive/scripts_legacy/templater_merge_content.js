<%*
const file = tp.file.find_tfile(tp.file.path)
let fm = tp.frontmatter
let updates = {}

if (!fm.slug || !String(fm.slug).trim()) {
  updates["slug"] = await tp.user.generate_slug({ file })
}

if (Object.keys(updates).length > 0) {
  await tp.file.apply_frontmatter(updates)
  new Notice("Slug backfilled")
} else {
  new Notice("Slug already present")
}

%>
