workbench_ingest_vault_content() {
  emulate -L zsh
  set -euo pipefail

  if [[ $# -ne 0 ]]; then
    echo "Usage: ingest_vault_content" >&2
    return 1
  fi

  local cmd
  for cmd in asc-select asc-ingest; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      echo "[ingest_vault_content] missing command: $cmd" >&2
      return 127
    fi
  done

  local tmpdir
  tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/ingest_vault_content.XXXXXX")"

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

  set +e
  asc-select sentinel \
    2> >(tee "${err_files[1]}" >&2) \
    | asc-select records \
      2> >(tee "${err_files[2]}" >&2) \
    | asc-ingest calls \
      2> >(tee "${err_files[3]}" >&2)
  pipeline_rc=$?
  statuses=("${pipestatus[@]}")
  set -e

  if (( pipeline_rc == 0 )); then
    rm -rf "$tmpdir"
    return 0
  fi

  local i
  local reported=0
  for i in 1 2 3; do
    if (( statuses[i] != 0 )); then
      reported=1
      echo "[ingest_vault_content] stage failed: ${stage_cmds[i]} (exit ${statuses[i]})" >&2
      if [[ -s "${err_files[i]}" ]]; then
        echo "[ingest_vault_content] stderr (${stage_cmds[i]}):" >&2
        cat "${err_files[i]}" >&2
      else
        echo "[ingest_vault_content] no stderr captured for ${stage_cmds[i]}" >&2
      fi
    fi
  done

  if (( reported == 0 )); then
    echo "[ingest_vault_content] pipeline failed with exit ${pipeline_rc} (no stage exit captured)" >&2
  fi

  rm -rf "$tmpdir"
  return "$pipeline_rc"
}

ingest_vault_content() {
  workbench_ingest_vault_content "$@"
}
