#!/usr/bin/env zsh
set -euo pipefail

# ------------------------------------------------------------
# Obsidian vault bootstrap (zsh-native)
# ------------------------------------------------------------

PROJECT_DIR=$PWD
PROJECT_NAME=${PROJECT_DIR:t}

# snake_case conversion (zsh-native)
VAULT_NAME=${PROJECT_NAME:l}
VAULT_NAME=${VAULT_NAME//[^a-z0-9]/_}
VAULT_NAME=${VAULT_NAME//__/_}
VAULT_NAME=${VAULT_NAME##_}
VAULT_NAME=${VAULT_NAME%%_}

VAULT_PATH="$PROJECT_DIR/$VAULT_NAME"
OBSIDIAN_SHARED="$HOME/library/obsidian"

print "Project    : $PROJECT_NAME"
print "Vault name : $VAULT_NAME"
print "Vault path : $VAULT_PATH"
print

# Safety checks
[[ -e $VAULT_PATH ]] && {
  print "ERROR: Vault directory already exists: $VAULT_PATH"
  exit 1
}

[[ ! -d $OBSIDIAN_SHARED ]] && {
  print "ERROR: Shared Obsidian directory not found: $OBSIDIAN_SHARED"
  exit 1
}

# ------------------------------------------------------------
# Create vault structure
# ------------------------------------------------------------

mkdir -p $VAULT_PATH/{\
00-system,\
01-notes,\
02-sources,\
03-drafts,\
04-output,\
attachments,\
.obsidian}

# ------------------------------------------------------------
# Symlink shared resources
# ------------------------------------------------------------

for dir in templates macros queries scripts; do
  if [[ -d $OBSIDIAN_SHARED/$dir ]]; then
    ln -s $OBSIDIAN_SHARED/$dir $VAULT_PATH/$dir
    print "Linked: $dir"
  else
    print "Skipped: $dir (not found)"
  fi
done

# ------------------------------------------------------------
# README
# ------------------------------------------------------------

cat > $VAULT_PATH/README.md <<EOF
# $PROJECT_NAME — Obsidian Vault

Vault folder: \`$VAULT_NAME\`

Shared resources are symlinked from:
\`$OBSIDIAN_SHARED\`

This vault is project-local and pipeline-consumable.
EOF

print
print "Obsidian vault created successfully."

