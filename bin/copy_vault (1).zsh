#!/usr/bin/env zsh
# create_vault.zsh — standalone script (not just a function)
# Purpose: From INSIDE a project folder, create a self-contained Obsidian vault
#          in /home/jeremy/Dropbox/<project_snake>_content by copying the
#          template at /home/jeremy/Dropbox/obsidian/VaultTemplate and
#          scaffolding ingest config + pandoc defaults.

set -euo pipefail

SRC="/home/jeremy/Dropbox/obsidian/VaultTemplate"
DEST_ROOT="/home/jeremy/Dropbox"

# ---- helpers ----
to_snake() {
  print -r -- "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/_/g; s/^_+|_+$//g'
}

aebort() { print -u2 -- "Error: $*"; exit 1 }

# ---- main ----
main() {
  [[ -d "$SRC" ]] || aebort "source vault '$SRC' not found"

  local project_name snake dest
  project_name="$(basename "$PWD")"
  [[ -n "$project_name" && "$project_name" != "/" ]] || aebort "could not determine project name from \$PWD"

  snake="$(to_snake "$project_name")"
  dest="$DEST_ROOT/${snake}_content"

  if [[ -e "$dest" ]]; then
    aebort "destination '$dest' already exists"
  fi

  print -- "Creating vault: $dest ..."
  mkdir -p "$dest"

  rsync -avh --progress "$SRC"/ "$dest"/ \
    --exclude='.DS_Store' \
    --exclude='Thumbs.db' \
    --exclude='.Trash*'

  # --- Ensure vault .ingest.yml reflects this project ---
  local ingest_yml="$dest/.ingest.yml"
  if [[ ! -f "$ingest_yml" ]]; then
    cat > "$ingest_yml" <<EOF
output_dir: passages
index_dir: indexes
category: import
split_pattern: "^#\\s+(.+)$"
meta:
  project: "${project_name}"
EOF
  else
    grep -qE '^meta:' "$ingest_yml" || printf '\nmeta:\n' >> "$ingest_yml"
    grep -qE '^\s*project:' "$ingest_yml" || printf '  project: "%s"\n' "$project_name" >> "$ingest_yml"
  fi

  # --- Scaffold project-level Pandoc defaults (non-destructive) ---
  mkdir -p ./pandoc
  if [[ ! -f ./pandoc/defaults_ingest.yaml ]]; then
    cat > ./pandoc/defaults_ingest.yaml <<'EOF'
from: gfm
to: gfm
wrap: none
metadata:
  category: translation
  # lang_pair: id-en
  # source_file: book.docx  # set at runtime or via script
filters: []
EOF
  fi
  if [[ ! -f ./pandoc/defaults_submit.yaml ]]; then
    cat > ./pandoc/defaults_submit.yaml <<'EOF'
from: gfm
to: pdf
pdf-engine: xelatex
wrap: none
metadata:
  project: ""  # filled by CI or script
filters: []
EOF
  fi

  print -- "✅ Vault created at: $dest"
  print -- "   Project Pandoc defaults at: $(realpath ./pandoc)"
}

main "$@"
