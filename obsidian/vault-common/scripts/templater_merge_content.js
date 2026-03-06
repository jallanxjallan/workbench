<%*

const file = tp.file.find_tfile(tp.file.path)

const required = {
  stage: "imported",
  state: "active",
  locked: false
}

let fm = tp.frontmatter

let updates = {}

for (let key in required) {
  if (!(key in fm)) {
    updates[key] = required[key]
  }
}

if (!("autoscribe" in fm)) {
  updates["autoscribe"] = {
    last_batch: "",
    last_step: "",
    revision: 0,
    updated: ""
  }
}

await tp.file.apply_frontmatter(updates)

new Notice("Frontmatter normalized (import detected)")

%>
