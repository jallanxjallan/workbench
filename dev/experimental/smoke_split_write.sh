#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON="${PYTHON:-/home/jeremy/Python3.13Env/bin/python}"
ADAPTERS="$ROOT/adapters/python"

VAULT_DIR="$(mktemp -d)"
OUTPUT_LOG="$(mktemp)"
trap 'rm -rf "$VAULT_DIR" "$OUTPUT_LOG"' EXIT

printf '%s\n' '{"content":"Alpha\n<!-- AS:SECTION -->\nBeta\n","stem":"Smoke Test","source_file":"tests/smoke.md"}' \
  | PYTHONPATH="$ADAPTERS" "$PYTHON" -m workbench.adapters.split_files --out-dir _new --digits 3 \
  | PYTHONPATH="$ADAPTERS" "$PYTHON" -m workbench.adapters.write_vault_files --base-dir "$VAULT_DIR" --mode writenew >"$OUTPUT_LOG"

FILE_ONE="$VAULT_DIR/_new/smoke_test/smoke_test--001.md"
FILE_TWO="$VAULT_DIR/_new/smoke_test/smoke_test--002.md"

[[ -f "$FILE_ONE" ]] || { echo "missing expected file: $FILE_ONE" >&2; exit 1; }
[[ -f "$FILE_TWO" ]] || { echo "missing expected file: $FILE_TWO" >&2; exit 1; }

diff -u <(printf 'Alpha\n') "$FILE_ONE"
diff -u <(printf 'Beta\n') "$FILE_TWO"

grep -q '"ok": true' "$OUTPUT_LOG" || {
  echo "writer output did not include successful records" >&2
  exit 1
}

echo "smoke-split-write passed (vault: $VAULT_DIR)"
