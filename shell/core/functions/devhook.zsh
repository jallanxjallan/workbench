#!/usr/bin/env zsh

# ------------------------------------------------------------
# Workbench devhook lifecycle
# ------------------------------------------------------------
# Core owns hook installation and environment lifecycle.
# This module applies runtime environment behavior.

: "${WORKBENCH_ROOT:=$HOME/Workbench}"
typeset -gi WORKBENCH_DEVHOOK_INITIALIZED=${WORKBENCH_DEVHOOK_INITIALIZED:-0}

typeset -g WORKBENCH_DEVHOOK_LAST_SCOPE_ALIASES="${WORKBENCH_DEVHOOK_LAST_SCOPE_ALIASES:-}"

workbench_devhook_unset_autoscribe_env() {
  emulate -L zsh
  local name
  local -a global_autoscribe_vars

  global_autoscribe_vars=()

  for name in ${(k)parameters}; do
    if [[ "$name" == AUTOSCRIBE_* ]] && (( ${global_autoscribe_vars[(Ie)$name]} == 0 )); then
      unset "$name"
    fi
  done
}

workbench_devhook_load_aliases() {
  emulate -L zsh
  local global_aliases="$WORKBENCH_ROOT/shell/aliases.zsh"

  [[ -f "$global_aliases" ]] && source "$global_aliases"

  WORKBENCH_DEVHOOK_LAST_SCOPE_ALIASES=""
}

workbench_devhook_apply_runtime_env() {
  emulate -L zsh
  source "$WORKBENCH_ROOT/shell/core/env/autoscribe.zsh"
  return 0
}

workbench_devhook_on_chpwd() {
  workbench_devhook_load_aliases
  workbench_devhook_apply_runtime_env
}

workbench_devhook_on_precmd() {
  workbench_devhook_apply_runtime_env
}

workbench_devhook_teardown() {
  emulate -L zsh
  return 0
}

workbench_devhook_init() {
  emulate -L zsh

  (( WORKBENCH_DEVHOOK_INITIALIZED )) && return 0

  autoload -Uz add-zsh-hook
  add-zsh-hook chpwd workbench_devhook_on_chpwd
  add-zsh-hook precmd workbench_devhook_on_precmd

  WORKBENCH_DEVHOOK_INITIALIZED=1

  workbench_devhook_load_aliases
  workbench_devhook_apply_runtime_env
}
