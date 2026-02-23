workbench_create_project() {
  local python_bin="${WORKBENCH_PYTHON:-/home/jeremy/Python3.13Env/bin/python}"
  local adapters_dir="$HOME/Workbench/adapters/python"
  PYTHONPATH="${adapters_dir}${PYTHONPATH:+:${PYTHONPATH}}" \
    "$python_bin" -m workbench.vault.create_project "$@"
}
