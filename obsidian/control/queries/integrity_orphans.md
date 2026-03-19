```dataview
TABLE file.name, length(file.inlinks) as inlinks, length(file.outlinks) as outlinks
FROM ""
WHERE !contains(file.path, "_control/")
WHERE length(file.inlinks) = 0 AND length(file.outlinks) = 0
SORT file.path ASC
```
