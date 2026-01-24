-- serialize.lua
-- Pandoc Lua filter to emit NDJSON of { filename, metadata, content } as the
-- document’s only output, by returning a new AST instead of exiting.

local utils = require 'pandoc.utils'

-- Convert MetaValue → Lua primitives
local function meta_to_lua(m)
  if m.t == 'MetaMap' then
    local tbl = {}
    for k, v in pairs(m) do tbl[k] = meta_to_lua(v) end
    return tbl
  elseif m.t == 'MetaList' then
    local arr = {}
    for _, v in ipairs(m) do arr[#arr + 1] = meta_to_lua(v) end
    return arr
  else
    return utils.stringify(m)
  end
end

-- JSON escaping & encoding
local function escape_str(s)
  local map = {
    ['"']  = '\\"', ['\\'] = '\\\\',
    ['\b'] = '\\b',  ['\f'] = '\\f',
    ['\n'] = '\\n',  ['\r'] = '\\r',
    ['\t'] = '\\t',
  }
  return s:gsub('[%z\1-\31\\"]', function(c)
    return map[c] or string.format("\\u%04x", c:byte())
  end)
end

local function to_json(v)
  local tp = type(v)
  if tp == 'string' then
    return '"' .. escape_str(v) .. '"'
  elseif tp == 'number' or tp == 'boolean' then
    return tostring(v)
  elseif tp == 'table' then
    -- array vs object?
    local is_array, max = true, 0
    for k in pairs(v) do
      if type(k) ~= 'number' then is_array = false break end
      max = math.max(max, k)
    end
    local parts = {}
    if is_array then
      for i=1,max do parts[#parts+1] = to_json(v[i]) end
      return '[' .. table.concat(parts, ',') .. ']'
    else
      for k,val in pairs(v) do
        parts[#parts+1] = '"' .. escape_str(k) .. '":' .. to_json(val)
      end
      return '{' .. table.concat(parts, ',') .. '}'
    end
  else
    return 'null'
  end
end

function Pandoc(doc)
  -- Figure out input filename (if any)
  local fn = ""
  if PANDOC_STATE.input_files and #PANDOC_STATE.input_files > 0 then
    fn = PANDOC_STATE.input_files[1]
  end

  -- Build our JSON-able table
  local out = {
    filepath = fn,
    metadata = meta_to_lua(doc.meta),
    content  = pandoc.write(doc, 'markdown')
  }

  local json = to_json(out)

  -- Return a brand-new AST with nothing but one RawBlock
  -- Pandoc will dump that raw Markdown directly to stdout
  local block = pandoc.RawBlock('markdown', json)
  return pandoc.Pandoc({ block }, {})
end
