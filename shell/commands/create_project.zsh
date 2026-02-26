workbench_create_project() {
  local wkb_bin=""
  if [[ -n "${WORKBENCH_ROOT:-}" && -x "${WORKBENCH_ROOT}/bin/wkb" ]]; then
    wkb_bin="${WORKBENCH_ROOT}/bin/wkb"
  else
    wkb_bin="$(command -v wkb || true)"
  fi
  if [[ -z "${wkb_bin}" ]]; then
    echo "wkb not found in PATH and WORKBENCH_ROOT/bin/wkb is unavailable" >&2
    return 1
  fi
  "$wkb_bin" create-project "$@"
}
