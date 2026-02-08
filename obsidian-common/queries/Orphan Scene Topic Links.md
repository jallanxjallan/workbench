```dataviewjs
const PROJECT_ROOT = "_project";
const TOPIC_SEGMENT = "/topics/";
const PASSAGE_SEGMENT = "/passages/";

// Build a set of all scene paths referenced by topics
const referenced = new Set();
for (const topic of dv.pages(`"${PROJECT_ROOT}"`).where(t => t.file.path.includes(TOPIC_SEGMENT)).array()) {
  const rel = topic.related_scenes ?? [];
  for (const link of rel) {
    if (link?.path) referenced.add(link.path);        // normal Dataview link
    else if (typeof link === "string") referenced.add(link); // fallback if stored as string
  }
}

// Get all stories not referenced by any topic
const unlinked = dv.pages(`"${PROJECT_ROOT}"`)
  .where(s => s.file.path.includes(PASSAGE_SEGMENT))
  .where(s => !referenced.has(s.file.path));

// Render a simple table
dv.table(["Unlinked Scenes"], unlinked.map(s => [s.file.link]));
```
