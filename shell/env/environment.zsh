#!/usr/bin/env zsh

# Static global anchors only (no cwd-sensitive behavior).
if [[ -z "${WORKBENCH_HOME:-}" || "${WORKBENCH_HOME}" == "$HOME/Workbench" ]]; then
  export WORKBENCH_HOME="$HOME/Workbench"
fi
if [[ -z "${AUTOSCRIBE_HOME:-}" || "${AUTOSCRIBE_HOME}" == "$HOME/Autoscribe" ]]; then
  export AUTOSCRIBE_HOME="$HOME/Autoscribe"
fi
if [[ -z "${STUDIO_ROOT:-}" ]]; then
  export STUDIO_ROOT="$HOME/Studio"
fi

# Backward compatibility for existing references.
export WORKBENCH_ROOT="$WORKBENCH_HOME"

export EDITOR=${EDITOR:-micro}
export PAGER=${PAGER:-less}
export LESS='-R'

path=(
  "$WORKBENCH_HOME/bin"
  "$HOME/Tools/bin"
  "$HOME/Python3.13Env/bin"
  "$HOME/.local/bin"
  $path
)
typeset -U path PATH
export PATH
