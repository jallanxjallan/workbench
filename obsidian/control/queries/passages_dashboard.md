```dataview
TABLE
slug,
project,
stage,
status,
wordcount(file.content) as words
FROM ""
WHERE !contains(file.path, "_control/")
SORT file.name ASC
```
