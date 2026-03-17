local function trim(text)
  return (text or ""):gsub("^%s+", ""):gsub("%s+$", "")
end

local captured_batch = nil

local function has_class(classes, target)
  for _, class_name in ipairs(classes or {}) do
    if class_name == target then
      return true
    end
  end
  return false
end

function Div(el)
  local classes = el.classes or {}
  if has_class(classes, "batch") then
    captured_batch = trim(pandoc.utils.stringify(el.content))
    return {}
  end

  if has_class(classes, "inline_instruction") then
    return el.content
  end
end

function Pandoc(doc)
  if captured_batch ~= nil and captured_batch ~= "" then
    doc.meta.batch = pandoc.MetaString(captured_batch)
  end
  return doc
end
