--!/usr/local/bin/lua


function Pandoc(doc)
  local title
  for k,v in pairs(doc.meta) do
    if k == "title" then
      title = pandoc.utils.stringify(v)
    end
  end
  if title ~= nil then
    table.insert (doc.blocks, 1, pandoc.Header(1, title))
  end
  return doc
  -- return pandoc.Pandoc(doc.blocks)
end
