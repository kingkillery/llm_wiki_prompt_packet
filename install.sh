#!/usr/bin/env bash
set -euo pipefail

VAULT="${1:-${LLM_WIKI_VAULT:-}}"
TARGETS="${2:-${LLM_WIKI_TARGETS:-claude,antigravity,codex,droid}}"
FORCE_FLAG="${3:-}"
REF="${4:-${LLM_WIKI_REF:-main}}"
REPO="kingkillery/llm_wiki_prompt_packet"

if [[ -z "$VAULT" ]]; then
  if [[ -r /dev/tty ]]; then
    exec 3</dev/tty
    read -r -p "Vault folder to index [current directory]: " VAULT <&3
  fi
  VAULT="${VAULT:-$PWD}"
fi

if [[ ! -d "$VAULT" ]]; then
  echo "Vault does not exist: $VAULT" >&2
  exit 1
fi

VAULT="$(cd "$VAULT" && pwd -P)"

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

if [[ "${LLM_WIKI_SKIP_SETUP:-0}" != "1" ]]; then
  SETUP_HELPER="$VAULT/scripts/setup_llm_wiki_memory.sh"
  if [[ ! -f "$SETUP_HELPER" ]]; then
    echo "Setup helper not found: $SETUP_HELPER" >&2
    exit 1
  fi
  bash "$SETUP_HELPER" --workspace "$VAULT"
fi
