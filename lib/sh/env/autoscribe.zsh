#!/usr/bin/env zsh

# ------------------------------------------------------------
# AutoScribe project environment
# ------------------------------------------------------------
#
# This file is sourced by devhook when entering a project
# working directory. It declares *context*, not execution
# truth.
#
# IMPORTANT DOCTRINE
# ------------------
# - Global instructions are executed from the instructions DB.
# - Filesystem instruction paths defined here are *authoring
#   overlays only*, not runtime authority.
# - All filesystem paths are resolved relative to CWD.
# - If a path does not exist, it is treated as absent.
# - No directories are created here.
#

# ------------------------------------------------------------
# Project identity
# ------------------------------------------------------------

# Absolute invariant: CWD is the project execution root
# devhook guarantees this before sourcing this file

# ------------------------------------------------------------
# Project root (authoring surface)
# ------------------------------------------------------------

# Canonical project root in the local project directory.
# Example:
#   /path/to/Projects
export AUTOSCRIBE_PROJECT_ROOT="${AUTOSCRIBE_PROJECT_ROOT:-}"
export AUTOSCRIBE_PROJECT_VAULT="${AUTOSCRIBE_PROJECT_VAULT:-}"
export AUTOSCRIBE_PROJECT_MNEMONIC="${AUTOSCRIBE_PROJECT_MNEMONIC:-}"
export AUTOSCRIBE_PROJECT_INSTRUCTIONS_ROOT="${AUTOSCRIBE_PROJECT_INSTRUCTIONS_ROOT:-}"

# ------------------------------------------------------------
# End of AutoScribe project environment
# ------------------------------------------------------------
