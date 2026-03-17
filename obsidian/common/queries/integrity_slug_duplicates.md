```dataview
TABLE slug, length(rows) as count
FROM "contents"
WHERE slug
GROUP BY slug
WHERE count > 1
```
