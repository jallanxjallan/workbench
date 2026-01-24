
function Pandoc(doc)
    abs_path = pandoc.path.join({pandoc.system.get_working_directory(), PANDOC_STATE['output_file']})
    url = 'file://'..abs_path
    print(url)
end
