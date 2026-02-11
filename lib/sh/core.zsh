#!/usr/bin/env zsh

# ------------------------------------------------------------
# Workbench shell core
# ------------------------------------------------------------
# Owns shell lifecycle wiring and delegates project context
# behavior to devhook.

: "${WORKBENCH_ROOT:=$HOME/Workbench}"

# Blessed commands
if (( ${path[(Ie)"$WORKBENCH_ROOT/bin"]} == 0 )); then
  path=("$WORKBENCH_ROOT/bin" $path)
fi

# Generic shell environment
if [[ -f "$WORKBENCH_ROOT/lib/sh/env/core.zsh" ]]; then
  source "$WORKBENCH_ROOT/lib/sh/env/core.zsh"
fi

# Function libraries
for config_file in "$WORKBENCH_ROOT"/lib/sh/lib/*.zsh(N); do
  source "$config_file"
done

# Lifecycle functions
for config_file in "$WORKBENCH_ROOT"/lib/sh/functions/*.zsh(N); do
  source "$config_file"
done

if typeset -f workbench_devhook_init >/dev/null 2>&1; then
  workbench_devhook_init
fi
