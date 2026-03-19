```dataview
TABLE file.name, file.folder, class, project, stage, status
FROM ""
WHERE !contains(file.path, "_control/")
WHERE !slug
SORT file.path ASC
```
