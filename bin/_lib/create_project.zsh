# create_project.zsh
#
# Upgrade an existing Obsidian vault into an AutoScribe project.
#
# Preconditions:
#   - Must be run from the intended project root
#   - A vault/ directory must already exist
#   - Project must not already be initialised
#
# Effects:
#   - Adds syslinks to Workbench instructions and common base
#   - Initialises git repository if missing
#   - Creates .env.local for devhook consumption
#
# This script is intentionally conservative:
#   - It never creates a vault
#   - It never overwrites existing project state
#

workbench_create_project() {
  emulate -L zsh
  set -euo pipefail

  if [[ $# -ne 0 ]]; then
    echo "Usage: create-project" >&2
    return 1
  fi

  local project_root="$PWD"
  local project_name
  project_name="$(basename "$project_root")"

  # --- require existing vault ---
  if [[ ! -d vault ]]; then
    echo "Error: no vault/ directory found in $project_root" >&2
    echo "Create a vault first (e.g. via Obsidian or create-vault-from-folder)." >&2
    return 1
  fi

  # --- refuse to re-initialise an existing project ---
  if [[ -f .env.local ]]; then
    echo "Error: this directory already appears to be an AutoScribe project." >&2
    echo "Found existing .env.local — refusing to re-run project initialisation." >&2
    return 1
  fi

  # --- validate Workbench ---
  if [[ -z "$WORKBENCH_INSTRUCTIONS" || ! -d "$WORKBENCH_INSTRUCTIONS" ]]; then
    echo "Error: WORKBENCH_INSTRUCTIONS not set or invalid." >&2
    return 1
  fi

  if [[ -z "$WORKBENCH_COMMON" || ! -d "$WORKBENCH_COMMON" ]]; then
    echo "Error: WORKBENCH_COMMON not set or invalid." >&2
    return 1
  fi

  # --- syslinks ---
  mkdir -p vault/_syslinks

  if [[ ! -e vault/_syslinks/instructions ]]; then
    ln -s "$WORKBENCH_INSTRUCTIONS" vault/_syslinks/instructions
  fi

  if [[ ! -e vault/_syslinks/common ]]; then
    ln -s "$WORKBENCH_COMMON" vault/_syslinks/common
  fi

  # --- editor-facing convenience links ---
  mkdir -p vault/instructions

  if [[ ! -e vault/instructions/_global ]]; then
    ln -s ../_syslinks/instructions vault/instructions/_global
  fi

  if [[ ! -e vault/common ]]; then
    ln -s _syslinks/common vault/common
  fi

  # --- devhook env mapping ---
  cat > .env.local <<EOF
# AutoScribe project environment (generated)
PROJECT_NAME="$project_name"
PROJECT_ROOT="$project_root"
PROJECT_VAULT="$project_root/vault"
EOF

  # --- git ---
  if [[ ! -d .git ]]; then
    git init >/dev/null || return 1

    cat > .gitignore <<'EOF'
.env.local
.DS_Store
__pycache__/
*.log
.vscode/
EOF

    git add .gitignore vault
    git commit -m "INIT project (vault + syslinks + env mapping)" >/dev/null
  fi

  echo "✅ AutoScribe project initialised"
  echo "   Project:  $project_name"
  echo "   Vault:    vault/"
  echo "   Syslinks: vault/_syslinks/{instructions,common}"
  echo "   Env:      .env.local"
}
