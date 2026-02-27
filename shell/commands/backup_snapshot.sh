#!/usr/bin/env bash
set -euo pipefail

TIMESTAMP=$(date +"%Y-%m-%dT%H-%M-%S")
AUTOSCRIBE="$HOME/Autoscribe"
WORKBENCH="$HOME/Workbench"
CONTENT_ROOT="${WORKBENCH_CONTENT_ROOT:-}"
PROJECTS_ROOT="$HOME/Projects"
AUTOSCRIBE_DB="$HOME/.local/share/autoscribe/db"
DROPBOX_ROOT="$HOME/Dropbox/Backups"
DROPBOX_PARENT="$HOME/Dropbox"

declare -a CREATED_ARCHIVES=()

log_section() {
    printf "\n=== %s ===\n" "$1"
}

die() {
    echo "ERROR: $*" >&2
    exit 1
}

trap 'echo "ERROR: backup-snapshot failed at line $LINENO" >&2' ERR

check_required_dir() {
    local dir="$1"
    [ -d "$dir" ] || die "Required directory missing: $dir"
}

create_archive() {
    local source="$1"
    local dest="$2"
    local source_parent
    local source_basename

    source_parent=$(dirname "$source")
    source_basename=$(basename "$source")

    if [ -f "$dest" ]; then
        echo "Refusing to overwrite existing archive: $dest" >&2
        exit 1
    fi

    tar -czf "$dest" \
        --exclude='*/node_modules' \
        --exclude='*/.venv' \
        --exclude='*/.cache' \
        --exclude='*/__pycache__' \
        -C "$source_parent" "$source_basename"

    CREATED_ARCHIVES+=("$dest")
    echo "Created: $dest"
}

log_section "Validating required paths"
[ -n "$CONTENT_ROOT" ] || die "WORKBENCH_CONTENT_ROOT is not set"
check_required_dir "$AUTOSCRIBE"
check_required_dir "$WORKBENCH"
check_required_dir "$CONTENT_ROOT"
check_required_dir "$PROJECTS_ROOT"
check_required_dir "$DROPBOX_PARENT"

log_section "Ensuring Dropbox backup directories"
mkdir -p "$DROPBOX_ROOT/autoscribe"
mkdir -p "$DROPBOX_ROOT/workbench"
mkdir -p "$DROPBOX_ROOT/content-root"
mkdir -p "$DROPBOX_ROOT/projects"
mkdir -p "$DROPBOX_ROOT/autoscribe-db"

log_section "Backing up Autoscribe"
create_archive "$AUTOSCRIBE" "$DROPBOX_ROOT/autoscribe/autoscribe-$TIMESTAMP.tar.gz"

log_section "Backing up Workbench"
create_archive "$WORKBENCH" "$DROPBOX_ROOT/workbench/workbench-$TIMESTAMP.tar.gz"

log_section "Backing up content root"
create_archive "$CONTENT_ROOT" "$DROPBOX_ROOT/content-root/content-root-$TIMESTAMP.tar.gz"

log_section "Backing up Git projects"
project_count=0
for dir in "$PROJECTS_ROOT"/*; do
    [ -d "$dir" ] || continue
    if [ -d "$dir/.git" ]; then
        project_name=$(basename "$dir")
        mkdir -p "$DROPBOX_ROOT/projects/$project_name"
        create_archive "$dir" "$DROPBOX_ROOT/projects/$project_name/${project_name}-${TIMESTAMP}.tar.gz"
        project_count=$((project_count + 1))
    fi
done

echo "Git projects archived: $project_count"

log_section "Backing up Autoscribe DB"
if [ -d "$AUTOSCRIBE_DB" ]; then
    create_archive "$AUTOSCRIBE_DB" "$DROPBOX_ROOT/autoscribe-db/autoscribe-db-$TIMESTAMP.tar.gz"
else
    echo "Skipping Autoscribe DB backup; directory not found: $AUTOSCRIBE_DB"
fi

archive_count=${#CREATED_ARCHIVES[@]}
[ "$archive_count" -gt 0 ] || die "No archives were created"

total_size_human=$(du -ch "${CREATED_ARCHIVES[@]}" | tail -n 1 | awk '{print $1}')
total_size_bytes=$(du -cb "${CREATED_ARCHIVES[@]}" | tail -n 1 | awk '{print $1}')

log_section "Backup summary"
echo "Timestamp: $TIMESTAMP"
echo "Archives created: $archive_count"
echo "Total snapshot size: $total_size_human ($total_size_bytes bytes)"
echo "Root destination: $DROPBOX_ROOT"

echo "backup-snapshot completed successfully"
