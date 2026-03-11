# Filters

## Lua

Store Lua filters in `filters/lua/` and run with:

```bash
pandoc input.md --lua-filter filters/lua/path/to/filter.lua -o out.md
```

## Python (panflute)

Store panflute filters in `filters/python/` and run with:

```bash
python3 -m pip install panflute
pandoc input.md --filter filters/python/path/to/filter.py -o out.md
```

Keep both filter families independent from Workbench internals.
