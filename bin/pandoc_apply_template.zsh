#!/usr/bin/env zsh

# pandoc_apply_template.zsh
#
# Apply a Pandoc template to one or more Markdown files with strong safety
# guarantees:
#   - path-scoped git cleanliness checks (staged + unstaged)
#   - atomic writeback via temp file
#   - optional dry-run (default)
#   - explicit --writeback required to modify files
#
# Intended for structural normalization (front matter, sentinels, ordering),
# not semantic rewriting.

set -o errexit
set -o nounset
set -o pipefail

usage() {
  cat <<'EOF'
Usage:
  pandoc_apply_template.zsh [--writeback] --template TEMPLATE file...

Options:
  --template TEMPLATE   Pandoc template file to apply (required)
  --writeback           Actually overwrite files (default is dry-run)
  -h, --help            Show this help

Behavior:
  - Refuses to modify any target file that has staged or unstaged git changes
  - In dry-run mode, writes output to a temp file and shows a diff
  - In writeback mode, overwrites files atomically
EOF
}

WRITEBACK=0
TEMPLATE=""
FILES=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --writeback)
      WRITEBACK=1
      shift
      ;;
    --template)
      TEMPLATE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      FILES+=("$1")
      shift
      ;;
  esac
done

if [[ -z "$TEMPLATE" || ${#FILES[@]} -eq 0 ]]; then
  usage >&2
  exit 1
fi

assert_clean_paths() {
  for f in "$@"; do
    git diff --quiet -- "$f" && git diff --cached --quiet -- "$f" || {
      echo "Refusing to modify $f: staged or unstaged changes" >&2
      return 1
    }
  done
}

assert_clean_paths "${FILES[@]}"

for f in "${FILES[@]}"; do
  tmp=$(mktemp "${f}.pandoc.XXXXXX")

  pandoc "$f" \
    --template "$TEMPLATE" \
    --from markdown \
    --to markdown \
    -o "$tmp"

  if [[ $WRITEBACK -eq 1 ]]; then
    mv "$tmp" "$f"
    echo "Updated $f"
  else
    echo "--- diff: $f (dry-run) ---"
    git diff --no-index "$f" "$tmp" || true
    rm "$tmp"
  fi
done

if [[ $WRITEBACK -eq 0 ]]; then
  echo "Dry-run complete. Re-run with --writeback to apply changes."
fi
