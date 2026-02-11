#!/usr/bin/env zsh

# ------------------------------------------------------------
# Workbench devhook lifecycle
# ------------------------------------------------------------
# Core owns hook installation and context lifecycle.
# This module implements project entry/exit behavior.

: "${WORKBENCH_ROOT:=$HOME/Workbench}"
typeset -gi WORKBENCH_DEVHOOK_INITIALIZED=${WORKBENCH_DEVHOOK_INITIALIZED:-0}

typeset -g WORKBENCH_DEVHOOK_LAST_PROJECT_ALIASES="${WORKBENCH_DEVHOOK_LAST_PROJECT_ALIASES:-}"

workbench_devhook_unset_autoscribe_env() {
  emulate -L zsh
  local name

  for name in ${(k)parameters}; do
    [[ "$name" == AUTOSCRIBE_* ]] && unset "$name"
  done
}

workbench_devhook_load_aliases() {
  emulate -L zsh
  local global_aliases="$WORKBENCH_ROOT/bin/aliases.zsh"

  [[ -f "$global_aliases" ]] && source "$global_aliases"

  WORKBENCH_DEVHOOK_LAST_PROJECT_ALIASES=""

  if [[ -n "${DIRENV_DIR:-}" ]]; then
    local project_aliases="${PROJECT_ALIASES:-$DIRENV_DIR/.aliases.zsh}"
    if [[ -f "$project_aliases" ]]; then
      source "$project_aliases"
      WORKBENCH_DEVHOOK_LAST_PROJECT_ALIASES="$project_aliases"
    fi
  fi
}

workbench_devhook_apply_project_context() {
  emulate -L zsh

  if [[ -n "${AUTOSCRIBE_PROJECT_ROOT:-}" ]]; then
    source "$WORKBENCH_ROOT/lib/sh/env/autoscribe.zsh"
    return 0
  fi

  workbench_devhook_unset_autoscribe_env
  return 0
}

workbench_devhook_on_chpwd() {
  workbench_devhook_load_aliases
  workbench_devhook_apply_project_context
}

workbench_devhook_on_precmd() {
  workbench_devhook_apply_project_context
}

workbench_devhook_teardown() {
  emulate -L zsh
  workbench_devhook_unset_autoscribe_env
}

workbench_devhook_init() {
  emulate -L zsh

  (( WORKBENCH_DEVHOOK_INITIALIZED )) && return 0

  autoload -Uz add-zsh-hook
  add-zsh-hook chpwd workbench_devhook_on_chpwd
  add-zsh-hook precmd workbench_devhook_on_precmd

  WORKBENCH_DEVHOOK_INITIALIZED=1

  workbench_devhook_load_aliases
  workbench_devhook_apply_project_context
}
