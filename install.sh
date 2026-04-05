#!/usr/bin/env bash
set -euo pipefail

VAULT="${1:-${LLM_WIKI_VAULT:-$PWD}}"
TARGETS="${2:-${LLM_WIKI_TARGETS:-claude,antigravity,codex,droid}}"
FORCE_FLAG="${3:-}"
REF="${4:-${LLM_WIKI_REF:-main}}"
REPO="kingkillery/llm_wiki_prompt_packet"

TMP_DIR="$(mktemp -d)"
ZIP_PATH="$TMP_DIR/packet.zip"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

curl -fsSL "https://github.com/${REPO}/archive/${REF}.zip" -o "$ZIP_PATH"
python3 - <<'PY' "$ZIP_PATH" "$TMP_DIR"
import sys
from pathlib import Path
from zipfile import ZipFile

zip_path = Path(sys.argv[1])
dest = Path(sys.argv[2])
with ZipFile(zip_path) as archive:
    archive.extractall(dest)
PY

PACKET_ROOT="$(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
if [[ -z "$PACKET_ROOT" ]]; then
  echo "Unable to find extracted packet root." >&2
  exit 1
fi

INSTALLER="$PACKET_ROOT/installers/install_obsidian_agent_memory.py"
if [[ ! -f "$INSTALLER" ]]; then
  echo "Installer not found in downloaded packet: $INSTALLER" >&2
  exit 1
fi

INSTALL_ARGS=("$INSTALLER" --vault "$VAULT" --targets "$TARGETS")
if [[ "$FORCE_FLAG" == "--force" || "${LLM_WIKI_FORCE:-0}" == "1" ]]; then
  INSTALL_ARGS+=(--force)
fi

python3 "${INSTALL_ARGS[@]}"
