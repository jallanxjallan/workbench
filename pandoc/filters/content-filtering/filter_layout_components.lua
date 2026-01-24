-- Pandoc Lua filter to keep only paragraphs whose first character matches an entry in the metadata "component" array
-- Usage: pandoc --lua-filter=filter_components.lua input.md -o output.md

return {
  {
    Pandoc = function(doc)
      -- Retrieve and validate the "component" list from metadata
      local metaComp = doc.meta.components
      if type(metaComp) ~= "table" then
        error("Pandoc filter error: 'component' metadata field is missing or not a list")
      end

      -- Build a set of component symbols
      local comps = {}
      for _, item in ipairs(metaComp) do
        local sym = pandoc.utils.stringify(item)
        comps[sym] = true
      end


-- Filter function: keep Para if its first character matches a component symbol,
-- but always pass through any paragraph that starts with an image.
local function filter_para(elem)
  -- 1) If the very first inline is an Image, leave the Para unchanged:
  local firstInline = elem.content[1]
  if firstInline and firstInline.t == "Image" then
  end

  -- 2) Otherwise, do your normal symbol test:
  local txt   = pandoc.utils.stringify(elem)
  local first = txt:match("^(" .. utf8.charpattern .. ")")
  print('symbol'..first)
  if comps[first] then 
    print('in comps'..first)
    return nil  -- keep this paragraph
  else
    return {}   -- remove this paragraph
  end
end


      -- Apply the paragraph filter across all blocks
      doc.blocks = pandoc.walk_block(pandoc.Div(doc.blocks), { Para = filter_para }).content
      return doc
    end
  }
}

