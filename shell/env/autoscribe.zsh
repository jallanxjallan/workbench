#!/usr/bin/env zsh

# Preserve optional runtime configuration variables without cwd switching.
export WORKBENCH_CONTENT_ROOT="${WORKBENCH_CONTENT_ROOT:-}"
export WORKBENCH_CONFIG_DIR="${WORKBENCH_CONFIG_DIR:-}"
export WORKBENCH_CACHE_DIR="${WORKBENCH_CACHE_DIR:-}"
