--!/usr/local/bin/lua
function Pandoc(doc)
    for key, value in pairs(doc.meta) do
        if key == 'header' then 
            local heading = pandoc.Header(1, pandoc.Strong(pandoc.utils.stringify(value)))
            table.insert(doc.blocks, 1, heading) 
            return doc
        end 
    end 
    return doc
end




