function ingest_vault_contents() {
  local batch_slug="$1"
  shift
  local python_bin="${WORKBENCH_PYTHON:-/home/jeremy/Python3.13Env/bin/python}"
  local pythonpath_root="${WORKBENCH_PYTHONPATH_ROOT:-$HOME/Workbench/cli}"

  PYTHONPATH="${pythonpath_root}${PYTHONPATH:+:${PYTHONPATH}}" \
    "$python_bin" -m workbench.adapters.select.select_sentinel --batch-slug "$batch_slug" "$@" \
  | PYTHONPATH="${pythonpath_root}${PYTHONPATH:+:${PYTHONPATH}}" \
      "$python_bin" -m workbench.adapters.select.select_records \
  | asc-ingest --batch "$batch_slug"
}
