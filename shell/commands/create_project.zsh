workbench_create_project() {
  local python_bin="${WORKBENCH_PYTHON:-/home/jeremy/Python3.13Env/bin/python}"
  local pythonpath_root="$HOME/Workbench/cli"
  PYTHONPATH="${pythonpath_root}${PYTHONPATH:+:${PYTHONPATH}}" \
    "$python_bin" -m workbench.vault.create_project "$@"
}
