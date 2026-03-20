#!/usr/bin/env zsh

# Static global anchors only (no cwd-sensitive behavior).
if [[ -z "${WORKBENCH_HOME:-}" || "${WORKBENCH_HOME}" == "$HOME/Workbench" ]]; then
  WORKBENCH_HOME="$HOME/Workbench"
fi
export WORKBENCH_HOME
if [[ -z "${AUTOSCRIBE_HOME:-}" || "${AUTOSCRIBE_HOME}" == "$HOME/Autoscribe" ]]; then
  AUTOSCRIBE_HOME="$HOME/Autoscribe"
fi
export AUTOSCRIBE_HOME
if [[ -z "${WORKBENCH_CONTROL_ROOT:-}" || "${WORKBENCH_CONTROL_ROOT}" == "$HOME/Projects/autoscribe-control" ]]; then
  WORKBENCH_CONTROL_ROOT="$HOME/Control"
fi
export WORKBENCH_CONTROL_ROOT
AUTOSCRIBE_CONTROL_ROOT="$WORKBENCH_CONTROL_ROOT"
export AUTOSCRIBE_CONTROL_ROOT
if [[ -z "${STUDIO_ROOT:-}" ]]; then
  STUDIO_ROOT="$HOME/Studio"
fi
export STUDIO_ROOT

# Backward compatibility for existing references.
export WORKBENCH_ROOT="$WORKBENCH_HOME"
export PANDOC_DATA_DIR="${PANDOC_DATA_DIR:-$WORKBENCH_HOME/tools/pandoc}"
export PANDOC_DATA_DIR="${PANDOC_DATA_DIR:-$WORKBENCH_HOME/tools/pandoc}"

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
