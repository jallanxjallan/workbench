function CodeBlock(el)
  return pandoc.Para({pandoc.Str(el.text)})
end

return {
  { CodeBlock = CodeBlock }
}

