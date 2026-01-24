#!/usr/bin/env zsh
set -euo pipefail

PROJECTS_DIR="$HOME/Projects"
BACKUP_DIR="$HOME/Dropbox/backups"
DRY_RUN=0

mkdir -p "$BACKUP_DIR"

timestamp=$(date +%F-%H%M)
archive="$BACKUP_DIR/projects-$timestamp.tar.gz"

# 1. Use an array properly by mapfile-style reading or using find's -print0
# In ZSH, we can use the (f) parameter expansion flag to split by lines safely,
# but using a null-terminated stream is even safer for weird filenames.
FILES=()
while IFS= read -r -d $'\0' line; do
    FILES+=("$line")
done < <(find "$PROJECTS_DIR" \( -type f -o -type d \) ! -type l ! -path '*/.*' -print0)

if (( ${#FILES[@]} == 0 )); then
  echo "Nothing eligible for backup."
  exit 0
fi

if (( DRY_RUN )); then
  echo "DRY RUN — The following ${#FILES[@]} items would be archived:"
  printf '  %s\n' "${FILES[@]}"
  exit 0
fi

# 2. Use --files-from=- to tell tar to read the null-terminated list from stdin
printf '%s\0' "${FILES[@]}" \
| tar --null -T - -czf "$archive"

echo "Backup created: $archive"