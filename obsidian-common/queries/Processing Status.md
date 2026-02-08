
# 🤖 Generated Scenes 
```dataview
TABLE WITHOUT ID file.link AS Scene, file.tags AS Tags
FROM "scenes"
WHERE status = "🤖" OR contains(string(status), "🤖")
SORT file.name ASC
```


# 📥 Queued Prompts
```dataview
TABLE WITHOUT ID file.link AS Scene, file.tags AS Tags
FROM "scenes"
WHERE queue = true
SORT file.name ASC
```

# 🕰️ Unqueued Prompts 
```dataview
TABLE WITHOUT ID file.link AS Scene, file.tags AS Tags
FROM "scenes"
WHERE status = "💬" OR contains(string(status), "💬")
and queue = false
SORT file.tags ASC
```
