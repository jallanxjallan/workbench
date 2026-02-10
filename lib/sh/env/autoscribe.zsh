# ------------------------------------------------------------
# AutoScribe environment
# Explicit. No defaults. No magic.
# ------------------------------------------------------------

# NOTE:
# Global instructions are executed from the instructions database.
# Any instruction-related filesystem paths in the shell environment are for
# authoring, migration, or bootstrap purposes only, not runtime execution.
# This file intentionally does not define instruction-root filesystem authority.
# Compatibility instruction roots (if exported elsewhere, e.g.
# AUTOSCRIBE_STUDIO_ROOT/STUDIO_INSTRUCTIONS_ROOT/AUTOSCRIBE_INSTRUCTIONS_ROOT)
# are authoring surfaces only.

# Application home (logs, caches, misc state)
export AUTOSCRIBE_HOME="$HOME/.local/share/autoscribe"

# Redis (runtime coordination)
export AUTOSCRIBE_REDIS_URL="redis://localhost:6379/0"

# SQLite (durable ledger / flight recorder, not instructions authority)
export AUTOSCRIBE_DB_PATH="$HOME/.local/share/autoscribe/db/autoscribe.sqlite"

# ------------------------------------------------------------
# Sanity checks
# ------------------------------------------------------------

: "${AUTOSCRIBE_HOME:?AUTOSCRIBE_HOME is not set}"
: "${AUTOSCRIBE_REDIS_URL:?AUTOSCRIBE_REDIS_URL is not set}"
: "${AUTOSCRIBE_DB_PATH:?AUTOSCRIBE_DB_PATH is not set}"

# ------------------------------------------------------------
# Non-destructive setup
# ------------------------------------------------------------

mkdir -p "$AUTOSCRIBE_HOME"
mkdir -p "$(dirname "$AUTOSCRIBE_DB_PATH")"
