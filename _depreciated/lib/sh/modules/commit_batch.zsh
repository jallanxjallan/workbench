workbench_batch_commit() {
  emulate -L zsh
  set -euo pipefail

  local message

  if [[ $# -lt 2 ]]; then
    echo "Usage: batch-commit \"Commit message\" file [file ...]" >&2
    return 1
  fi

  message="$1"
  shift

  git reset >/dev/null 2>&1
  git add "$@"
  git commit --allow-empty -m "$message"

  echo "Checkpoint created: $message"
}
