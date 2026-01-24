# create_vault
# Run this *from inside a project folder*. It will:
#  1) Copy the Obsidian template from /home/jeremy/Dropbox/obsidian/VaultTemplate
#     to /home/jeremy/Dropbox/<project_snake>_content
#  2) Set the project name in the new vault's .ingest.yml (creating it if missing)
#  3) Scaffold project-level Pandoc defaults for *ingestion* and *submission*
#     under ./pandoc/ (without overwriting existing files)
#
# Example:
#   cd ~/Repos/HHP-LawFirm
#   create_vault  # -> /home/jeremy/Dropbox/hhp_law_firm_content
create_vault() {
  local src="/home/jeremy/Dropbox/obsidian/VaultTemplate"
  local project_name snake dest

  project_name="$(basename "$PWD")"
  # to_snake: lowercase, collapse non-alnum to underscore, trim underscores
  snake="$(echo "$project_name" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/_/g; s/^_+|_+$//g')"
  dest="/home/jeremy/Dropbox/${snake}_content"

  if [[ ! -d "$src" ]]; then
    echo "Error: source vault '$src' not found." >&2
    return 1
  fi
  if [[ -z "$project_name" || "$project_name" == "/" ]]; then
    echo "Error: could not determine project name from \$PWD." >&2
    return 1
  fi
  if [[ -e "$dest" ]]; then
    echo "Error: destination '$dest' already exists." >&2
    return 1
  fi

  echo "Creating vault: $dest ..."
  mkdir -p "$dest"
  rsync -avh --progress "$src"/ "$dest"/ \
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
    # idempotently ensure meta.project is set (simple append if missing)
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

  echo "✅ Vault created at: $dest"
  echo "   Project Pandoc defaults at: $(realpath ./pandoc)"
}
