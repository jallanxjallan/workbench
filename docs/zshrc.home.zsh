# ==============================# Environment Variables
# ==============================
env_path="/home/jeremy/Python3.13Env"
source "$env_path/bin/activate"



# --- COLOR OUTPUT ---
# Keep color enabled (no NO_COLOR / TERM overrides).
# ---------------------------------

# Zoxide Custom Configuration
export _ZO_EXCLUDE_DIRS="$HOME/Downloads:$HOME/Desktop"
export _ZO_ECHO="1"

export _ZO_FZF_OPTS="--height=50% --layout=reverse --border=rounded --margin=1,1"

# Initialize zoxide (Must be after config settings)
eval "$(zoxide init zsh)"


# =============================
# SECRETS
# =============================
SECRETS_FILE="$HOME/.zshenv_secrets"
if [[ -f "$SECRETS_FILE" ]]; 
then 
    source "$SECRETS_FILE" 
fi

# ==============================
# Aliases
# ==============================


# ==============================
# Functions
# ==============================
# WorkBench PATH is configured in the canonical loader below.


# ==============================
# History Settings
# ==============================
HISTFILE=~/.zsh_history 
HISTSIZE=100000 
SAVEHIST=100000 

setopt SHARE_HISTORY 
setopt APPEND_HISTORY 
setopt EXTENDED_HISTORY 
setopt HIST_IGNORE_SPACE 
setopt HIST_IGNORE_DUPS 



# ==============================
# Prompt and Completion
# ==============================
# Set a simple, colored prompt
PROMPT='%n@%m %F{green}%c%f %# '


# Define a custom highlight style for comment lines
# zstyle ':completion:*:default' highlight-style comment 'fg=red'


# ==============================
# Scripting Safety
# ==============================
# Fail-fast defaults for safe scripting
#set -euo pipefail 


# direnv integration
eval "$(direnv hook zsh)"

# Source per-project aliases when you cd into a direnv-managed folder
autoload -Uz add-zsh-hook

load_project_aliases() {
  local global_aliases="/home/jeremy/Workbench/bin/aliases.zsh"
  [[ -f "$global_aliases" ]] && source "$global_aliases"

  if [[ -n "$DIRENV_DIR" ]]; then
    local f="${PROJECT_ALIASES:-$DIRENV_DIR/.aliases.zsh}"
    [[ -f "$f" ]] && source "$f"
  fi
}

# Run on every dir change and once for the current dir
add-zsh-hook chpwd load_project_aliases
load_project_aliases

export CHROME_PATH=/usr/bin/google-chrome-stable
# Force clear to use the ANSI sequence that works for this NUC
alias clear='printf "\033[2J\033[H"'

# Fix Ctrl-L to use the same logic
function redraw-and-clear() {
    printf "\033[2J\033[H"
    zle redisplay
}
zle -N redraw-and-clear
bindkey '^L' redraw-and-clear

# ------------------------------------------------------------
# WorkBench loader (canonical)
# ------------------------------------------------------------

# Blessed commands
export PATH="$HOME/Workbench/bin:$PATH"

# Shell configuration (explicitly sourced)
for config_file in \
  $HOME/Workbench/bin/aliases.zsh \
  $HOME/Workbench/bin/_env/*.zsh(N) \
  $HOME/Workbench/bin/_lib/*.zsh(N); do
  source "$config_file"
done
