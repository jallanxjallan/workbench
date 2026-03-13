#!/usr/bin/env zsh

set -euo pipefail

if (( $# > 0 )); then
  roots=("$@")
else
  roots=(".")
fi

files=("${(@f)$(rg '^batch_id:' -l -- "${roots[@]}")}")
if (( ${#files[@]} == 0 )); then
  print "No batch_id fields found."
  exit 0
fi

sed -i 's/^batch_id:/batch:/' "${files[@]}"

print "Updated files:"
printf '%s\n' "${files[@]}"
print
print "Verification:"
rg '^batch:' -- "${roots[@]}"
