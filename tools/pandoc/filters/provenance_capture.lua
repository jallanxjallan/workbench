function Meta(meta)
  local origin = pandoc.MetaMap({})

  for key, value in pairs(meta) do
    origin[key] = value
    meta[key] = nil
  end

  meta.origin = origin
  return meta
end
