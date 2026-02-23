function ingest_vault_contents() {
  local batch_slug="$1"
  shift

  select-sentinel --batch-slug "$batch_slug" "$@" \
  | select-records \
  | asc-ingest --batch "$batch_slug"
}
