```dataview
TABLE
slug,
project,
content_kind,
stage,
status,
wordcount(file.content) as words
FROM ""
WHERE !contains(file.path, "_control/") AND class = "content"
SORT file.name ASC
```
