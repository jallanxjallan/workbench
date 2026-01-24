local changed_files = nil

-- Get the list of changed files since the last SUBMIT commit
function get_changed_files()
  local handle = io.popen("git log --grep='^SUBMIT:' --pretty=format:'%H' -n 1")
  local last_submit = handle:read("*a"):match("%S+")
  handle:close()

  if not last_submit then
    io.stderr:write("⚠️  No SUBMIT commit found. Treating all files as changed.\n")
    return nil
  end

  local diff_cmd = "git diff --name-only " .. last_submit .. " HEAD"
  local handle = io.popen(diff_cmd)
  local output = handle:read("*a")
  handle:close()

  local files = {}
  for line in output:gmatch("[^\r\n]+") do
    files[line] = true
  end
  return files
end

function is_local_file(path)
  return not path:match("^https?://") and not path:match("^mailto:")
end

function is_file_modified(path)
  if not changed_files then
    changed_files = get_changed_files()
    if not changed_files then return true end  -- default to true if no submit
  end
  return changed_files[path] == true
end

function Para(el)
  local new_inlines = {}
  local has_links = false
  local has_modified_link = false

  for _, inline in ipairs(el.content) do
    if inline.t == "Link" then
      has_links = true
      local target = inline.target[1]
      if is_local_file(target) and not is_file_modified(target) then
        -- Skip unchanged local file link
      else
        table.insert(new_inlines, inline)
        has_modified_link = true
      end
    else
      table.insert(new_inlines, inline)
    end
  end

  -- Only remove the Para if it had links, but none were to modified files
  if has_links and not has_modified_link then
    return nil
  else
    return pandoc.Para(new_inlines)
  end
end

