md_to_ndjson() {
  emulate -L zsh

  jq -Rsc '
    def dequote:
      if ((startswith("\"") and endswith("\"")) or (startswith("'"'"'") and endswith("'"'"'")))
      then .[1:-1]
      else .
      end;

    . as $raw
    | if ($raw | startswith("---\n")) and ($raw | test("^---\\n([\\s\\S]*?)\\n---\\n"))
      then
        ($raw | capture("^---\\n(?<meta>[\\s\\S]*?)\\n---\\n(?<body>[\\s\\S]*)$")) as $doc
        | ($doc.meta
            | split("\n")
            | map(select(test("^[[:space:]]*filepath:[[:space:]]*")))
            | .[0]? // ""
            | sub("^[[:space:]]*filepath:[[:space:]]*"; "")
            | gsub("^[[:space:]]+|[[:space:]]+$"; "")
            | dequote
          ) as $filepath
        | {
            content: ($doc.body | sub("^\\n"; "") | sub("\\n$"; "")),
            input_record: (if $filepath == "" then {} else { filepath: $filepath } end)
          }
      else
        {
          content: ($raw | sub("\\n$"; "")),
          input_record: {}
        }
      end
  '
}

md_to_json() {
  md_to_ndjson
}

workbench_ingest_external_files() {
  emulate -L zsh
  setopt localoptions pipefail

  if ! command -v pandoc >/dev/null 2>&1; then
    echo "ingest_external_files: missing command: pandoc" >&2
    return 127
  fi
  if ! command -v jq >/dev/null 2>&1; then
    echo "ingest_external_files: missing command: jq" >&2
    return 127
  fi
  if ! command -v asc >/dev/null 2>&1; then
    echo "ingest_external_files: missing command: asc" >&2
    return 127
  fi

  if [[ -t 0 && $# -eq 0 ]]; then
    echo "ingest_external_files: provide file paths on stdin or as arguments" >&2
    return 1
  fi

  if (( $# > 0 )); then
    printf "%s\n" "$@"
  else
    cat
  fi \
    | xargs -n1 pandoc -d filters -t markdown \
    | md_to_ndjson \
    | asc ingest calls
}

ingest_external_files() {
  workbench_ingest_external_files "$@"
}
