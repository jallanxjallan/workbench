# Filters

Filters are organized by function rather than by workflow.

Workflows are assembled through Pandoc defaults files, which select and order
reusable filters for a given pipeline.

Lua filters live under `filters/lua/`.
Python panflute filters live under `filters/python/panflute/`.

Filters in this tree should remain independent, composable, and reusable.
