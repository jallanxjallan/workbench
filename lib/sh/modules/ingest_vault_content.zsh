workbench_ingest_classify_stdout() {
  emulate -L zsh

  local output="$1"
  local line
  local trimmed_line
  for line in ${(f)output}; do
    if [[ -z "${line//[[:space:]]/}" ]]; then
      continue
    fi

    trimmed_line="${line#"${line%%[![:space:]]*}"}"
    if [[ "$trimmed_line" == \{* ]]; then
      echo "ndjson"
    else
      echo "message"
    fi
    return 0
  done

  echo "empty"
}

workbench_ingest_print_stage_stderr() {
  emulate -L zsh

  local stage_name="$1"
  local err_file="$2"
  local line

  [[ -s "$err_file" ]] || return 0

  while IFS= read -r line || [[ -n "$line" ]]; do
    echo "[${stage_name}] ${line}" >&2
  done < "$err_file"
}

workbench_ingest_has_clean_already_ingested_notice() {
  emulate -L zsh

  local err_file="$1"
  local line
  [[ -s "$err_file" ]] || return 1

  # Sentinel can emit this informational line when nothing actionable remains.
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" == *"all selected files are clean; assuming already ingested"* ]] && return 0
  done < "$err_file"

  return 1
}

workbench_ingest_vault_content() {
  emulate -L zsh
  setopt localoptions localtraps pipefail

  if [[ $# -ne 0 ]]; then
    echo "ingest_vault_content: usage: ingest_vault_content" >&2
    return 1
  fi

  if [[ "$PWD" == "/" ]]; then
    echo "ingest_vault_content: run from a project directory, not /" >&2
    return 1
  fi

  local -a select_sentinel_cmd
  local -a select_records_cmd
  local -a ingest_calls_cmd
  if ! command -v asc >/dev/null 2>&1; then
    echo "ingest_vault_content: missing command: asc" >&2
    return 127
  fi
  select_sentinel_cmd=(asc select sentinel)
  select_records_cmd=(asc select records)
  ingest_calls_cmd=(asc ingest calls)

  local tmpdir
  tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/ingest_vault_content.XXXXXX")" || {
    echo "ingest_vault_content: failed to create temp directory" >&2
    return 1
  }

  trap '[[ -n "${tmpdir:-}" ]] && rm -rf "$tmpdir"' EXIT

  local select_sentinel_err="$tmpdir/select_sentinel.stderr"
  local select_records_err="$tmpdir/select_records.stderr"
  local ingest_calls_err="$tmpdir/ingest_calls.stderr"

  local stage_kind=""
  local stage_status=0
  local partial_seen=0

  local select_output=""
  select_output="$("${select_sentinel_cmd[@]}" 2>"$select_sentinel_err")"
  stage_status=$?
  stage_kind="$(workbench_ingest_classify_stdout "$select_output")"
  workbench_ingest_print_stage_stderr "select sentinel" "$select_sentinel_err"

  if workbench_ingest_has_clean_already_ingested_notice "$select_sentinel_err"; then
    return 0
  fi

  if (( stage_status == 0 )); then
    case "$stage_kind" in
      ndjson) ;;
      message)
        printf "%s\n" "$select_output"
        return 0
        ;;
      empty)
        return 0
        ;;
    esac
  elif (( stage_status == 1 )); then
    if [[ "$stage_kind" == "ndjson" ]]; then
      partial_seen=1
    else
      [[ -n "$select_output" ]] && printf "%s\n" "$select_output" >&2
      echo "ingest_vault_content: select sentinel aborted" >&2
      return 1
    fi
  else
    [[ -n "$select_output" ]] && printf "%s\n" "$select_output" >&2
    echo "ingest_vault_content: select sentinel failed (${stage_status})" >&2
    return 1
  fi

  local records_output=""
  records_output="$(printf "%s\n" "$select_output" | "${select_records_cmd[@]}" 2>"$select_records_err")"
  stage_status=$?
  stage_kind="$(workbench_ingest_classify_stdout "$records_output")"
  workbench_ingest_print_stage_stderr "select records" "$select_records_err"

  if (( stage_status == 0 )); then
    case "$stage_kind" in
      ndjson) ;;
      message)
        printf "%s\n" "$records_output"
        return "$partial_seen"
        ;;
      empty)
        return "$partial_seen"
        ;;
    esac
  elif (( stage_status == 1 )); then
    if [[ "$stage_kind" == "ndjson" ]]; then
      partial_seen=1
    else
      [[ -n "$records_output" ]] && printf "%s\n" "$records_output" >&2
      echo "ingest_vault_content: select records aborted" >&2
      return 1
    fi
  else
    [[ -n "$records_output" ]] && printf "%s\n" "$records_output" >&2
    echo "ingest_vault_content: select records failed (${stage_status})" >&2
    return 1
  fi

  local ingest_output=""
  ingest_output="$(printf "%s\n" "$records_output" | "${ingest_calls_cmd[@]}" 2>"$ingest_calls_err")"
  stage_status=$?
  workbench_ingest_print_stage_stderr "ingest calls" "$ingest_calls_err"

  if (( stage_status == 0 )); then
    [[ -n "$ingest_output" ]] && printf "%s\n" "$ingest_output"
    return "$partial_seen"
  fi

  if (( stage_status == 1 )); then
    [[ -n "$ingest_output" ]] && printf "%s\n" "$ingest_output"
    return 1
  fi

  [[ -n "$ingest_output" ]] && printf "%s\n" "$ingest_output" >&2
  echo "ingest_vault_content: ingest calls failed (${stage_status})" >&2
  return 1
}

ingest_vault_content() {
  workbench_ingest_vault_content "$@"
}
