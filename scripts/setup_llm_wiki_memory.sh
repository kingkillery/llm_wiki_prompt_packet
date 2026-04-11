#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TARGET_SCRIPT="$WORKSPACE_ROOT/support/scripts/setup_llm_wiki_memory.sh"

if [[ ! -f "$TARGET_SCRIPT" ]]; then
  echo "Setup helper not found: $TARGET_SCRIPT" >&2
  exit 1
fi

cd "$WORKSPACE_ROOT"
exec bash "$TARGET_SCRIPT" "$@"
