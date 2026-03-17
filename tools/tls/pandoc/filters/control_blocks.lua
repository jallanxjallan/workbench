local script = debug.getinfo(1, "S").source:sub(2)
local dir = script:match("(.*/)")

dofile(dir .. "lua/metadata/control_blocks.lua")
