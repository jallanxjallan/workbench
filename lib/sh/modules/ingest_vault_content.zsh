workbench_ingest_vault_content() {
  emulate -L zsh
  setopt localoptions pipefail

  if [[ $# -ne 0 ]]; then
    echo "ingest_vault_content: usage: ingest_vault_content" >&2
    return 1
  fi

  if [[ "$PWD" == "/" ]]; then
    echo "ingest_vault_content: run from a project directory, not /" >&2
    return 1
  fi

  local cmd
  for cmd in asc-select asc-ingest; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      echo "ingest_vault_content: missing command: $cmd" >&2
      return 127
    fi
  done

  local tmpdir
  tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/ingest_vault_content.XXXXXX")" || {
    echo "ingest_vault_content: failed to create temp directory" >&2
    return 1
  }

  local -a stage_cmds
  stage_cmds=(
    "asc-select sentinel"
    "asc-select records"
    "asc-ingest calls"
  )

  local -a err_files
  err_files=(
    "$tmpdir/select_sentinel.stderr"
    "$tmpdir/select_records.stderr"
    "$tmpdir/ingest_calls.stderr"
  )

  local pipeline_rc
  local -a statuses
  asc-select sentinel \
    2> "${err_files[1]}" \
    | asc-select records \
      2> "${err_files[2]}" \
    | asc-ingest calls \
      2> "${err_files[3]}"
  pipeline_rc=$?
  statuses=("${pipestatus[@]}")

  if (( pipeline_rc == 0 )); then
    rm -rf "$tmpdir"
    return 0
  fi

  local i
  local failed_stage=""
  local failed_rc="$pipeline_rc"
  local first_error_line=""
  for i in 1 2 3; do
    if (( statuses[i] != 0 )); then
      failed_stage="${stage_cmds[i]}"
      failed_rc="${statuses[i]}"
      if [[ -s "${err_files[i]}" ]]; then
        IFS= read -r first_error_line < "${err_files[i]}" || true
      fi
      break
    fi
  done

  rm -rf "$tmpdir"

  if [[ -n "$failed_stage" ]]; then
    if [[ -n "$first_error_line" ]]; then
      echo "ingest_vault_content: ${failed_stage} failed (${failed_rc}): ${first_error_line}" >&2
    else
      echo "ingest_vault_content: ${failed_stage} failed (${failed_rc})" >&2
    fi
  else
    echo "ingest_vault_content: pipeline failed (${pipeline_rc})" >&2
  fi

  return 1
}

ingest_vault_content() {
  workbench_ingest_vault_content "$@"
}
