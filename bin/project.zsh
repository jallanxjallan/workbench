# Project (vault + git) utilities


create_project() {
local name="$1"
local base="$HOME/Projects/$name"


if [[ -d "$base" ]]; then
echo "Project already exists: $base" >&2
return 1
fi


# --- create structure ---
mkdir -p "$base/vault/00-system"
mkdir -p "$base/code"


# --- initialise git repo ---
git init "$base" >/dev/null
(
cd "$base" || return
cat > .gitignore <<'EOF'
.DS_Store
*.log
.vscode/
__pycache__/
EOF
git add .gitignore
git commit -m "INIT project skeleton (vault + code)" >/dev/null
)


echo "Project created at $base"
}


copy_project_vault() {
rsync -av --delete "$1/vault/" "$2/vault/"
}

# Vault utilities


create_vault() {
local name="$1"
mkdir -p "$HOME/Vaults/$name/00-system"
}


copy_vault() {
rsync -av --delete "$1/" "$2/"
}