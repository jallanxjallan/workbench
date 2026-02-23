function ingest_vault_contents() {
  local batch_slug="$1"
  shift
  local python_bin="${WORKBENCH_PYTHON:-/home/jeremy/Python3.13Env/bin/python}"
  local adapters_dir="${WORKBENCH_ADAPTERS_PYTHON:-$HOME/Workbench/adapters/python}"

  PYTHONPATH="${adapters_dir}${PYTHONPATH:+:${PYTHONPATH}}" \
    "$python_bin" -m workbench.adapters.select.select_sentinel --batch-slug "$batch_slug" "$@" \
  | PYTHONPATH="${adapters_dir}${PYTHONPATH:+:${PYTHONPATH}}" \
      "$python_bin" -m workbench.adapters.select.select_records \
  | asc-ingest --batch "$batch_slug"
}
