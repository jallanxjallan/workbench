```dataview
TABLE slug, length(rows) as count
FROM ""
WHERE !contains(file.path, "_control/") AND slug
GROUP BY slug
WHERE count > 1
```
