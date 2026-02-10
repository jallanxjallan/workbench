# ------------------------------------------------------------
# AutoScribe environment
# Explicit. No defaults. No magic.
# ------------------------------------------------------------

# Application home (logs, caches, misc state)
export AUTOSCRIBE_HOME="$HOME/.local/share/autoscribe"

# Redis (runtime coordination)
export AUTOSCRIBE_REDIS_URL="redis://localhost:6379/0"

# SQLite (durable ledger / flight recorder)
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

