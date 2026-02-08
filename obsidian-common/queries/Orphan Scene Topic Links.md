```dataviewjs
// Build a set of all scene paths referenced by topics
const referenced = new Set();
for (const topic of dv.pages('"topics"').array()) {
  const rel = topic.related_scenes ?? [];
  for (const link of rel) {
    if (link?.path) referenced.add(link.path);        // normal Dataview link
    else if (typeof link === "string") referenced.add(link); // fallback if stored as string
  }
}

// Get all stories not referenced by any topic
const unlinked = dv.pages('"scenes"')
  .where(s => !referenced.has(s.file.path));

// Render a simple table
dv.table(["Unlinked Scenes"], unlinked.map(s => [s.file.link]));

```
