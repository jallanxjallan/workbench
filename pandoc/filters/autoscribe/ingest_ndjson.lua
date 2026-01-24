-- ingest_ndjson.lua
--
-- Pandoc Lua filter to ingest NDJSON records and convert them to documents.
-- Inverse operation of emit_ndjson.lua
--
-- Reads a single NDJSON record from stdin before pandoc processes input,
-- then reconstructs a complete Pandoc document from that record.
--
-- Responsibilities:
-- - Read NDJSON record from stdin (consumes one line before pandoc reads)
-- - Extract content field and parse as Markdown into document body
-- - Extract all other fields and inject as document metadata
-- - Completely replace any input document with the NDJSON content
--
-- Expected usage:
--   ndjson_emitter | pandoc --lua-filter=ingest_ndjson.lua -t docx -o output.docx
--   cat records.ndjson | pandoc --lua-filter=ingest_ndjson.lua -t html -o output.html
--
-- Note: No input file or document is specified. The NDJSON stream is the only input.

local json = require("pandoc.json")

-- Global state: store the NDJSON record for the Pandoc function
local ndjson_record = nil

-- Read NDJSON from stdin on initialization
local function read_ndjson_from_stdin()
  local line = io.read()
  if line then
    local success, record = pcall(json.decode, line)
    if success then
      return record
    else
      io.stderr:write("Error parsing NDJSON: " .. tostring(record) .. "\n")
      return nil
    end
  end
  return nil
end

-- Helper: parse Markdown string into Pandoc document AST
local function markdown_to_blocks(markdown_str)
  if not markdown_str or markdown_str == "" then
    return {}
  end
  -- Parse markdown into a document, then extract blocks
  local doc = pandoc.read(markdown_str, "markdown")
  return doc.blocks
end

-- Helper: convert Lua table to Pandoc MetaValue
local function lua_to_meta(value)
  if type(value) == "string" then
    return pandoc.MetaString(value)
  elseif type(value) == "number" then
    return pandoc.MetaString(tostring(value))
  elseif type(value) == "boolean" then
    return pandoc.MetaBool(value)
  elseif type(value) == "table" then
    -- Check if it's a list or a map
    if #value > 0 then
      -- It's a list
      local metalist = {}
      for _, item in ipairs(value) do
        table.insert(metalist, lua_to_meta(item))
      end
      return pandoc.MetaList(metalist)
    else
      -- It's a map
      local metamap = {}
      for key, item in pairs(value) do
        metamap[key] = lua_to_meta(item)
      end
      return pandoc.MetaMap(metamap)
    end
  else
    return pandoc.MetaString(tostring(value))
  end
end

-- Read NDJSON on first filter invocation
if not ndjson_record then
  ndjson_record = read_ndjson_from_stdin()
  if not ndjson_record then
    io.stderr:write("Error: ingest_ndjson requires NDJSON from stdin\n")
    os.exit(1)
  end
end

function Pandoc(doc)
  -- Reconstruct document from NDJSON record
  local new_meta = {}
  local content_blocks = {}
  
  -- Extract content field and convert to blocks
  if ndjson_record.content then
    content_blocks = markdown_to_blocks(ndjson_record.content)
  end
  
  -- Extract all other fields and add to metadata
  for key, value in pairs(ndjson_record) do
    if key ~= "content" then
      new_meta[key] = lua_to_meta(value)
    end
  end
  
  return pandoc.Pandoc(content_blocks, new_meta)
end
