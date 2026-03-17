function Meta(meta)
  local origin = pandoc.MetaMap({})
  local reserved = {
    batch = true,
  }

  for key, value in pairs(meta) do
    if not reserved[key] then
      origin[key] = value
      meta[key] = nil
    end
  end

  meta.origin = origin
  return meta
end
