#!/usr/bin/env zsh

# ------------------------------------------------------------
# Workbench shell core
# ------------------------------------------------------------
# Owns static shell wiring for Workbench commands and anchors.

if [[ -z "${WORKBENCH_HOME:-}" || "${WORKBENCH_HOME}" == "$HOME/Workbench" ]]; then
  export WORKBENCH_HOME="$HOME/Workbench"
fi

if [[ -z "${AUTOSCRIBE_HOME:-}" || "${AUTOSCRIBE_HOME}" == "$HOME/Autoscribe" ]]; then
  export AUTOSCRIBE_HOME="$HOME/Autoscribe"
fi

if [[ -z "${STUDIO_ROOT:-}" ]]; then
  export STUDIO_ROOT="$HOME/Studio"
fi

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
