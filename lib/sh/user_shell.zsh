#!/usr/bin/env zsh

# ------------------------------------------------------------
# User shell customizations
# ------------------------------------------------------------
# Central loader for Workbench shell core, aliases, and user
# functions so ~/.zshrc only needs one source line.

: "${WORKBENCH_ROOT:=$HOME/Workbench}"

if [[ -f "$WORKBENCH_ROOT/lib/sh/core.zsh" ]]; then
  source "$WORKBENCH_ROOT/lib/sh/core.zsh"
fi

if [[ -f "$HOME/.work_aliases.zsh" ]]; then
  source "$HOME/.work_aliases.zsh"
fi

if [[ -f "$HOME/.work_functions.zsh" ]]; then
  source "$HOME/.work_functions.zsh"
fi

# Force clear to use the ANSI sequence that works for this NUC
alias clear='printf "\\033[2J\\033[H"'

# Fix Ctrl-L to use the same logic
function redraw-and-clear() {
  printf "\\033[2J\\033[H"
  zle redisplay
}
zle -N redraw-and-clear
bindkey ^L redraw-and-clear
