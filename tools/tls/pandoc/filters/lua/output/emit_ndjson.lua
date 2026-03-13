local top_level_fields = {
  batch_slug = true,
  assets = true,
  priority = true,
  context = true,
  origin = true,
}

local valid_blocks = {
  Para = true,
  Plain = true,
  CodeBlock = true,
  BlockQuote = true,
  BulletList = true,
  OrderedList = true,
  DefinitionList = true,
  Table = true,
}

local function has_meaningful_blocks(blocks)
  for _, block in ipairs(blocks or {}) do
    if valid_blocks[block.t] then
      return true
    end
    if block.t == "Div" and has_meaningful_blocks(block.content) then
      return true
    end
  end
  return false
end

local function meta_to_lua(value)
  if value == nil then
    return nil
  end
  local kind = pandoc.utils.type(value)
  if kind == "Inlines" then
    return pandoc.utils.stringify(value)
  end
  if kind == "Blocks" then
    return pandoc.write(pandoc.Pandoc(value), "markdown")
  end
  if kind == "List" then
    local items = {}
    for _, item in ipairs(value) do
      items[#items + 1] = meta_to_lua(item)
    end
    return items
  end
  if type(value) ~= "table" then
    return value
  end
  if not value.t then
    local mapped = {}
    if #value > 0 then
      for _, item in ipairs(value) do
        mapped[#mapped + 1] = meta_to_lua(item)
      end
    else
      for key, item in pairs(value) do
        mapped[key] = meta_to_lua(item)
      end
    end
    return mapped
  end
  if value.t == "MetaString" then
    return value.text or value.c or pandoc.utils.stringify(value)
  end
  if value.t == "MetaBool" then
    return value.c
  end
  if value.t == "MetaInlines" then
    return pandoc.utils.stringify(value)
  end
  if value.t == "MetaBlocks" then
    return pandoc.write(pandoc.Pandoc(value), "markdown")
  end
  if value.t == "MetaList" then
    local items = {}
    for _, item in ipairs(value) do
      items[#items + 1] = meta_to_lua(item)
    end
    return items
  end
  if value.t == "MetaMap" then
    local mapped = {}
    for key, item in pairs(value) do
      mapped[key] = meta_to_lua(item)
    end
    return mapped
  end
  return pandoc.utils.stringify(value)
end

local function prune_empty(value)
  if value == nil then
    return nil
  end
  if type(value) ~= "table" then
    if type(value) == "string" and value:match("^%s*$") then
      return nil
    end
    return value
  end

  local pruned = {}
  if #value > 0 then
    for _, item in ipairs(value) do
      local cleaned = prune_empty(item)
      if cleaned ~= nil then
        pruned[#pruned + 1] = cleaned
      end
    end
  else
    for key, item in pairs(value) do
      local cleaned = prune_empty(item)
      if cleaned ~= nil then
        pruned[key] = cleaned
      end
    end
  end

  return next(pruned) and pruned or nil
end

local function fail_empty(doc)
  io.stderr:write("emit_ndjson: document empty after filters\n")
  if doc.meta.origin then
    local origin = prune_empty(meta_to_lua(doc.meta.origin))
    if type(origin) == "table" then
      io.stderr:write("origin: " .. pandoc.json.encode(origin) .. "\n")
    else
      io.stderr:write("origin: " .. tostring(origin) .. "\n")
    end
  end
  local slug = doc.meta.slug
  if not slug and doc.meta.origin and doc.meta.origin.slug then
    slug = doc.meta.origin.slug
  end
  if slug then
    io.stderr:write("slug: " .. pandoc.utils.stringify(slug) .. "\n")
  end
  os.exit(1)
end

function Pandoc(doc)
  if not has_meaningful_blocks(doc.blocks) then
    fail_empty(doc)
  end

  local content = pandoc.write(doc, "markdown")
  if not content or content:match("^%s*$") then
    fail_empty(doc)
  end

  local record = { content = content }
  local input_record = {}

  for key, value in pairs(doc.meta or {}) do
    local plain = prune_empty(meta_to_lua(value))
    if plain ~= nil then
      if top_level_fields[key] then
        record[key] = plain
      else
        input_record[key] = plain
      end
    end
  end

  input_record = prune_empty(input_record)
  if input_record ~= nil then
    record.input_record = input_record
  end

  print(pandoc.json.encode(prune_empty(record)))
  os.exit()
end
