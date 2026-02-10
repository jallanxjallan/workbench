# Core environment variables (generic)

export EDITOR=${EDITOR:-micro}
export PAGER=${PAGER:-less}
export LESS='-R'

# Path hygiene
path=(
  $HOME/.local/bin
  $path
)
