function url_decode(url)
    url = url:gsub("%%(%x%x)", function(hex)
        return string.char(tonumber(hex, 16))
    end)
    return url
end


local decoded_path = url_decode(url_path):gsub("file://", "")
