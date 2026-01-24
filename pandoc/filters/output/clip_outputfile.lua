-- Pandoc Lua filter to copy the output path to the clipboard on a Linux machine
-- Requires `xclip` to be installed on the system

function Pandoc(doc)
  -- Retrieve the output file path from PANDOC_STATE
  local output_path = PANDOC_STATE["output_file"]

  if output_path then
    -- Use xclip to copy the path to the clipboard
    local command = string.format("echo -n '%s' | xclip -selection clipboard", output_path)
    local success, exit_code, _ = os.execute(command)
    
    if not success then
      io.stderr:write("Failed to copy output path to clipboard\n")
    end
  else
    io.stderr:write("No output file found in PANDOC_STATE\n")
  end
  return doc
end

