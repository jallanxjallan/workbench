```dataview
TABLE file.name, slug, project, stage, status
FROM ""
WHERE !contains(file.path, "_control/")
WHERE slug AND (!project OR !stage OR !status)
SORT file.path ASC
```
