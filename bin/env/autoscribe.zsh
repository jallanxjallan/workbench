# AutoScribe / workflow environment

export AUTOSCRIBE_HOME="$HOME/.local/share/autoscribe"
export AUTOSCRIBE_REDIS_URL=${AUTOSCRIBE_REDIS_URL:-"redis://localhost:6379/0"}
export AUTOSCRIBE_DB_PATH=${WORKFLOW_DB_PATH:-"$HOME/.local/share/workflow/v2.db"}
export AUTOSCRIBE_INSTRUCTIONS_VAULT="$AUTOSCRIBE_HOME/instructions-vault"
