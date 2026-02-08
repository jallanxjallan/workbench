#!/usr/bin/env zsh
emulate -L zsh
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  obsidian-vault-sanity.zsh [VAULT_PATH]

Default:
  VAULT_PATH="$PWD"
EOF
}

die() {
  print -u2 -- "ERROR: $*"
  exit 1
}

vault_path="${1:-$PWD}"
if [[ "${1-}" == "-h" || "${1-}" == "--help" ]]; then
  usage
  exit 0
fi

realpath_bin="$(command -v realpath || true)"
[[ -n "$realpath_bin" ]] || die "realpath is required"
readlink_bin="$(command -v readlink || true)"
[[ -n "$readlink_bin" ]] || die "readlink is required"

[[ -d "$vault_path" ]] || die "Vault directory not found: $vault_path"
vault_path="$("$realpath_bin" "$vault_path")"

failures=0
warnings=0

pass() {
  print "PASS: $*"
}

warn() {
  warnings=$(( warnings + 1 ))
  print "WARN: $*"
}

fail() {
  failures=$(( failures + 1 ))
  print "FAIL: $*"
}

check_link() {
  local name="$1"
  local path="$vault_path/$name"
  local target_raw
  local target_abs

  if [[ ! -L "$path" ]]; then
    fail "$name is missing or not a symlink ($path)"
    return
  fi

  target_raw="$("$readlink_bin" "$path")"
  if [[ "$target_raw" == /* ]]; then
    warn "$name is absolute ($target_raw); prefer relative links"
  else
    pass "$name uses a relative target ($target_raw)"
  fi

  if ! target_abs="$("$realpath_bin" "$path" 2>/dev/null)"; then
    fail "$name is broken ($path -> $target_raw)"
    return
  fi
  pass "$name resolves to $target_abs"

  if [[ "$target_abs" == "$vault_path" || "$target_abs" == "$vault_path/"* ]]; then
    fail "$name resolves back into the vault; potential circular linkage"
  fi

  if [[ -w "$target_abs" ]]; then
    warn "$name target is writable by current user ($target_abs); keep read-only by convention"
  else
    pass "$name target is not writable by current user"
  fi
}

check_link "_project"
check_link "_common"

if [[ -L "$vault_path/common" ]]; then
  common_target="$("$readlink_bin" "$vault_path/common")"
  if [[ "$common_target" != "_common" ]]; then
    warn "legacy common link points to '$common_target' (expected '_common')"
  else
    pass "legacy common link points to _common"
  fi
fi

if [[ -L "$vault_path/_common" ]]; then
  common_abs="$("$realpath_bin" "$vault_path/_common" 2>/dev/null || true)"
  if [[ -n "$common_abs" ]]; then
    scan_paths=()
    for p in "$common_abs/templates" "$common_abs/scripts" "$common_abs/queries"; do
      [[ -d "$p" ]] && scan_paths+=("$p")
    done

    if (( ${#scan_paths[@]} > 0 )) && rg -n --hidden --glob '!*.git*' "/home/|obsidian://open\\?vault=" "${scan_paths[@]}" >/tmp/obsidian_common_path_hits.txt 2>/dev/null; then
      warn "_common content has absolute-path or fixed-vault references"
      sed -n '1,8p' /tmp/obsidian_common_path_hits.txt
    else
      pass "_common has no obvious fixed-vault or /home absolute-path references"
    fi
  fi
fi

print
if (( failures > 0 )); then
  print "Result: FAIL ($failures failure(s), $warnings warning(s))"
  exit 1
fi

print "Result: PASS ($warnings warning(s))"
