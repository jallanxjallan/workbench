-- filter_stale_links.lua

local changed_files = {}
local submission_commit = nil

local function capture(cmd)
  local f = io.popen(cmd, "r")
  if not f then return "" end
  local output = f:read("*all")
  f:close()
  return output
end

function prepare(meta)
  -- Check if user provided commit
  if meta["submission-commit"] then
    submission_commit = pandoc.utils.stringify(meta["submission-commit"]):gsub("%s+", "")
    -- Verify the commit actually exists
    local verify = capture("git cat-file -t " .. submission_commit)
    if verify:match("^commit") then
      io.stderr:write("Using user-provided submission commit: " .. submission_commit .. "\n")
    else
      io.stderr:write("Error: Provided submission commit does not exist: " .. submission_commit .. "\n")
      os.exit(1)  -- Hard exit with error
    end
  else
    -- Auto-detect latest Submission commit
    submission_commit = capture("git log --grep=Submission --pretty=format:%H -n 1"):gsub("%s+", "")
    if submission_commit ~= "" then
      io.stderr:write("Auto-detected latest Submission commit: " .. submission_commit .. "\n")
    else
      io.stderr:write("Warning: No Submission commit found! Will assume all files changed.\n")
      return
    end
  end

  -- Get changed files
  local diff_output = capture("git diff --name-only " .. submission_commit .. " HEAD")
  for line in diff_output:gmatch("[^\r\n]+") do
    changed_files[line] = true
  end
end

function Para(para)
  local links_in_para = {}
  local has_md_links = false

  for _, elem in ipairs(para.content) do
    if elem.t == "Link" and elem.target:match("%.md$") then
      table.insert(links_in_para, elem.target)
      has_md_links = true
    end
  end

  if has_md_links then
    for _, path in ipairs(links_in_para) do
      if changed_files[path] then
        return nil  -- Paragraph contains changed link, keep it
      end
    end
    return {}  -- No linked files changed, delete the paragraph
  else
    return nil  -- Paragraph without links, untouched
  end
end
