#!/usr/bin/env zsh

# ------------------------------------------------------------
# Workbench shell core
# ------------------------------------------------------------
# Owns static shell wiring for Workbench commands and anchors.

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

export WORKBENCH_ROOT="$WORKBENCH_HOME"

# Global environment anchors
if [[ -f "$WORKBENCH_HOME/shell/env/environment.zsh" ]]; then
  source "$WORKBENCH_HOME/shell/env/environment.zsh"
fi
if [[ -f "$WORKBENCH_HOME/shell/env/autoscribe.zsh" ]]; then
  source "$WORKBENCH_HOME/shell/env/autoscribe.zsh"
fi

# Global aliases and shell commands
if [[ -f "$WORKBENCH_HOME/shell/aliases.zsh" ]]; then
  source "$WORKBENCH_HOME/shell/aliases.zsh"
fi
for config_file in "$WORKBENCH_HOME"/shell/commands/*.zsh(N); do
  source "$config_file"
done
