function CodeBlock(el)
  local items = {}
  for line in el.text:gmatch("([^\n]+)") do
    table.insert(items, pandoc.Plain({pandoc.Str(line)}))
  end
  return pandoc.BulletList(items)
end

return {
  { CodeBlock = CodeBlock }
}

