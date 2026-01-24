--!/usr/local/bin/lua
function Pandoc(doc)
    for key, value in pairs(doc.meta) do
        if key == 'image' then 
            local image = pandoc.Header(1, pandoc.Strong(pandoc.utils.stringify(value)))
            table.insert(doc.blocks, 0, image) 
            return doc
        end 
    end 
    return doc
end



