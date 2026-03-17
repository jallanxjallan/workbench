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

local function detect_source_descriptor()
  local input_files = (PANDOC_STATE and PANDOC_STATE.input_files) or {}
  local first = input_files[1]
  if first and first ~= "" and first ~= "-" then
    return {
      source_type = "file",
      path = first,
    }, pandoc.path.filename(first)
  end
  return {
    source_type = "stdin",
  }, nil
end

local function fail_empty(doc)
  local origin = nil
  if doc.meta.origin then
    origin = prune_empty(meta_to_lua(doc.meta.origin))
  end

  io.stderr:write("emit_ndjson: document empty after filters\n")
  if origin ~= nil then
    if type(origin) == "table" then
      io.stderr:write("origin: " .. pandoc.json.encode(origin) .. "\n")
    else
      io.stderr:write("origin: " .. tostring(origin) .. "\n")
    end
  end
  if type(origin) == "table" and origin.slug then
    io.stderr:write("slug: " .. tostring(origin.slug) .. "\n")
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

  local detected_origin, filename_hint = detect_source_descriptor()
  local input_record = {}
  local origin = {}

  for key, value in pairs(doc.meta or {}) do
    local plain = prune_empty(meta_to_lua(value))
    if plain ~= nil then
      if key == "origin" and type(plain) == "table" then
        for origin_key, origin_value in pairs(plain) do
          origin[origin_key] = origin_value
        end
      else
        input_record[key] = plain
      end
    end
  end

  if type(origin.filename_hint) == "string" and origin.filename_hint:match("%S") then
    filename_hint = origin.filename_hint
    origin.filename_hint = nil
  end

  for key, value in pairs(detected_origin) do
    if origin[key] == nil then
      origin[key] = value
    end
  end

  input_record.origin = prune_empty(origin) or { source_type = detected_origin.source_type }
  if filename_hint and filename_hint:match("%S") then
    input_record.filename_hint = filename_hint
  end

  input_record = prune_empty(input_record) or { origin = { source_type = detected_origin.source_type } }
  if input_record.origin == nil then
    input_record.origin = { source_type = detected_origin.source_type }
  end

  local payload = {
    content = content,
    input_record = input_record,
  }
  if type(input_record.batch) == "string" and input_record.batch:match("%S") then
    payload.batch_slug = input_record.batch
  end

  print(pandoc.json.encode(payload))
  os.exit()
end
