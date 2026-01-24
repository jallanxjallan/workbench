
function Meta(meta) 
  meta['inputfile'] = PANDOC_STATE['input_files'][1]
  meta['outputfile'] = PANDOC_STATE['output_file'] 
  return meta
end
