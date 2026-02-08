# File & path helpers

mkcd() {
  mkdir -p "$1" && cd "$1"
}

backup_file() {
  cp "$1" "$1.bak.$(date +%Y%m%d-%H%M%S)"
}

safe_rm() {
  mv "$@" ~/.Trash/
}