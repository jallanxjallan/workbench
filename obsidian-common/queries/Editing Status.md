# Draft
```dataview
TABLE WITHOUT ID file.link AS Scene, status AS Status
FROM "_project"
WHERE status = "🔳" OR status = "✍️" or status = "📝" or status = "💡"
SORT file.name ASC
```
# In Process
```dataview
TABLE WITHOUT ID file.link AS Scene, status AS Status
FROM "_project"
WHERE status = "🤖" OR status = "💬" or status = "🧐"
SORT file.name ASC
```
# Editing
```dataviewjs

const statuses = ["🛑", "🔍", "🔧"];

dv.table(
  ["Scene", "Status"],
  dv.pages('"_project"')
    .where(p => statuses.includes(p.status))
    .sort(p => p.file.name, 'asc')
    .map(p => [p.file.link, p.status])
);
```

## Final
```dataviewjs

const statuses = ["✨", "✅"];

dv.table(
  ["Scene", "Status"],
  dv.pages('"_project"')
    .where(p => statuses.includes(p.status))
    .sort(p => p.file.name, 'asc')
    .map(p => [p.file.link, p.status])
);
```
