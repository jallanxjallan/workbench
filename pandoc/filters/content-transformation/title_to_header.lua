--!/usr/local/bin/lua
function Pandoc(doc)
    for key, value in pairs(doc.meta) do
        if key == "title" then 
            local heading = pandoc.Header(1, pandoc.utils.stringify(value))
            table.insert(doc.blocks, 1, heading) 
            return doc
        end 
    end 
    return doc
end



