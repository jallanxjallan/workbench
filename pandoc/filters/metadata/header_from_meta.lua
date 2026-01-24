--!/usr/local/bin/lua


function Pandoc(doc)
  local header
  for k,v in pairs(doc.meta) do
    if k == "header" then
      header = pandoc.utils.stringify(v)
    end
  end
  if header ~= nil then
    table.insert (doc.blocks, 1, pandoc.Header(1, header))
  end
  return doc
  -- return pandoc.Pandoc(doc.blocks)
end
