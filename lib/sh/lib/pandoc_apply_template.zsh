workbench_pandoc_apply_template_usage() {
  cat <<'EOF'
Usage:
  pandoc-apply-template [--writeback] --template TEMPLATE file...
EOF
}

workbench_pandoc_apply_template() {
  emulate -L zsh
  set -euo pipefail

  local writeback=0
  local template=""
  local f tmp
  local -a files=()

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --writeback)
        writeback=1
        shift
        ;;
      --template)
        template="$2"
        shift 2
        ;;
      -h|--help)
        workbench_pandoc_apply_template_usage
        return 0
        ;;
      *)
        files+=("$1")
        shift
        ;;
    esac
  done

  if [[ -z "$template" || ${#files[@]} -eq 0 ]]; then
    workbench_pandoc_apply_template_usage >&2
    return 1
  fi

  for f in "${files[@]}"; do
    git diff --quiet -- "$f" && git diff --cached --quiet -- "$f" || {
      echo "Refusing to modify $f: staged or unstaged changes" >&2
      return 1
    }
  done

  for f in "${files[@]}"; do
    tmp="$(mktemp "${f}.pandoc.XXXXXX")"

    pandoc "$f" \
      --template "$template" \
      --from markdown \
      --to markdown \
      -o "$tmp"

    if [[ $writeback -eq 1 ]]; then
      mv "$tmp" "$f"
      echo "Updated $f"
    else
      echo "--- diff: $f (dry-run) ---"
      git diff --no-index "$f" "$tmp" || true
      rm "$tmp"
    fi
  done

  if [[ $writeback -eq 0 ]]; then
    echo "Dry-run complete. Re-run with --writeback to apply changes."
  fi
}
