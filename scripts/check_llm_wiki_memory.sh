#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TARGET_SCRIPT="$WORKSPACE_ROOT/support/scripts/check_llm_wiki_memory.sh"

if [[ ! -f "$TARGET_SCRIPT" ]]; then
  echo "Check helper not found: $TARGET_SCRIPT" >&2
  exit 1
fi

cd "$WORKSPACE_ROOT"
HAS_WORKSPACE=0
for arg in "$@"; do
  if [[ "$arg" == "--workspace" || "$arg" == --workspace=* ]]; then
    HAS_WORKSPACE=1
    break
  fi
done

if [[ "$HAS_WORKSPACE" -eq 1 ]]; then
  exec bash "$TARGET_SCRIPT" "$@"
fi

exec bash "$TARGET_SCRIPT" --workspace "$WORKSPACE_ROOT" "$@"
