#!/bin/zsh

# Usage: ./vault_checkpoint.zsh "Commit Message" "path/to/file1.md" "path/to/file2.md" ...

# 1. Grab the first argument as the message
MESSAGE=$1
shift # This removes the message from the argument list, leaving only file paths

# 2. Check if we actually have files to process
if [ $# -eq 0 ]; then
    echo "Error: No file paths provided."
    exit 1
fi

# 3. Clean the Staging Area (The "Loading Dock")
# This ensures other 'dirty' files aren't accidentally included.
# 'git reset' is safe; it moves staged files back to 'modified' status.
git reset > /dev/null 2>&1

# 4. Stage ONLY the files passed to the script
# Using "$@" handles spaces in filenames correctly in Zsh
git add "$@"

# 5. Create the checkpoint
# --allow-empty ensures the commit happens even if the file hasn't changed yet
git commit --allow-empty -m "$MESSAGE"

echo "Checkpoint created: $MESSAGE"
