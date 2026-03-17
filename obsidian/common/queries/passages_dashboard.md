```dataview
TABLE
slug,
project,
stage,
status,
wordcount(file.content) as words
FROM "contents"
WHERE slug
SORT file.name ASC
```
