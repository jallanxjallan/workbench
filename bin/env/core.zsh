# Core environment variables (generic)

export EDITOR=${EDITOR:-nvim}
export PAGER=${PAGER:-less}
export LESS='-R'

# Path hygiene
path=(
  $HOME/.local/bin
  $path
)