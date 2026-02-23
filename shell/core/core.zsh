#!/usr/bin/env zsh

# ------------------------------------------------------------
# Workbench shell core
# ------------------------------------------------------------
# Owns shell lifecycle wiring and delegates project context
# behavior to devhook.

: "${WORKBENCH_ROOT:=$HOME/Workbench}"

# Generic shell environment
if [[ -f "$WORKBENCH_ROOT/shell/core/env/core.zsh" ]]; then
  source "$WORKBENCH_ROOT/shell/core/env/core.zsh"
fi

# Shell modules
for config_file in "$WORKBENCH_ROOT"/shell/modules/*.zsh(N); do
  source "$config_file"
done

# Lifecycle functions
for config_file in "$WORKBENCH_ROOT"/shell/core/functions/*.zsh(N); do
  source "$config_file"
done

if typeset -f workbench_devhook_init >/dev/null 2>&1; then
  workbench_devhook_init
fi
