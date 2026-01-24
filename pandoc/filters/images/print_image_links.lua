-- Strip Image Links Lua Filter for Pandoc
function Image(el)
	print(el)
  -- Return nil to remove the image element
  return nil
end