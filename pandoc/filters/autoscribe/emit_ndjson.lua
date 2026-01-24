-- autoscribe_ndjson.lua
--
-- Pandoc Lua filter to emit a single NDJSON record per invocation
-- for AutoScribe external ingest.
--
-- Responsibilities:
-- - Capture normalized document content (Markdown)
-- - Capture provenance (source type + URI)
-- - Emit exactly ONE NDJSON object to stdout
-- - Do NOT transform the document structure
--
-- Non-responsibilities:
-- - No batching logic
-- - No ULID generation
-- - No inference or guessing
-- - No file discovery
--
-- Expected usage:
--   pandoc -d ingest_files.yaml <file>
--   pandoc -d ingest_html.yaml <url>
--   ... | asc ingest external

local json = require("pandoc.json")

-- Helper: stringify document as Markdown
local function doc_to_markdown(doc)
  return pandoc.write(doc, "markdown")
end

function Pandoc(doc)
  -- ------------------------------------------------------------
  -- Source type: provided via Pandoc metadata
  -- e.g. autoscribe_source: file | web | stdin | train
  -- ------------------------------------------------------------
  local source = "unknown"
  if doc.meta.autoscribe_source then
    source = pandoc.utils.stringify(doc.meta.autoscribe_source)
  end

 -- ------------------------------------------------------------
  -- URI: Pandoc passes input files via PANDOC_STATE.input_files
  -- Under xargs -n 1 this will be a single-element list
  -- ------------------------------------------------------------
  local uri = nil
  if PANDOC_STATE and PANDOC_STATE.input_files then
    if #PANDOC_STATE.input_files > 0 then
      uri = PANDOC_STATE.input_files[1]
    end
  end

  -- ------------------------------------------------------------
  -- Build NDJSON record
  -- ------------------------------------------------------------
  local record = {
    content = doc_to_markdown(doc),
    origin = {
      scheme = source,
      uri = uri,
    },
    meta = {
      source_type = source,
    }
  }

  -- Emit NDJSON (single line)
  io.write(json.encode(record))
  io.write("\n")

  -- IMPORTANT:
  -- Return an empty document so Pandoc emits nothing else
  return pandoc.Pandoc({}, doc.meta)
end
