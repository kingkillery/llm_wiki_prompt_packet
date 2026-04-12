#!/usr/bin/env bash
set -euo pipefail

is_windows_bash() {
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) return 0 ;;
    *) return 1 ;;
  esac
}

is_wsl() {
  if [[ -n "${WSL_INTEROP:-}" || -n "${WSL_DISTRO_NAME:-}" ]]; then
    return 0
  fi
  grep -qi microsoft /proc/version 2>/dev/null
}

to_win_path() {
  local path="$1"
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -w "$path"
    return 0
  fi
  if command -v wslpath >/dev/null 2>&1; then
    wslpath -w "$path"
    return 0
  fi
  printf '%s\n' "$path"
}

INSTALL_SCOPE="${LLM_WIKI_INSTALL_SCOPE:-local}"
POSITIONAL=()
for arg in "$@"; do
  case "$arg" in
    -g|--global-install)
      INSTALL_SCOPE="global"
      ;;
    --local-install)
      INSTALL_SCOPE="local"
      ;;
    *)
      POSITIONAL+=("$arg")
      ;;
  esac
done
set -- "${POSITIONAL[@]}"

VAULT="${1:-${LLM_WIKI_VAULT:-}}"
TARGETS="${2:-${LLM_WIKI_TARGETS:-claude,antigravity,codex,droid}}"
FORCE_FLAG="${3:-}"
REF="${4:-${LLM_WIKI_REF:-main}}"
REPO="kingkillery/llm_wiki_prompt_packet"
INSTALL_MODE="${LLM_WIKI_INSTALL_MODE:-packet}"
export LLM_WIKI_INSTALL_SCOPE="$INSTALL_SCOPE"

if (is_windows_bash || is_wsl) && command -v powershell.exe >/dev/null 2>&1; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  PS1_PATH="$SCRIPT_DIR/install.ps1"
  if [[ -f "$PS1_PATH" ]]; then
    export LLM_WIKI_VAULT="$(to_win_path "${VAULT:-$PWD}")"
    export LLM_WIKI_TARGETS="$TARGETS"
    export LLM_WIKI_REF="$REF"
    export LLM_WIKI_INSTALL_MODE="$INSTALL_MODE"
    if [[ "$FORCE_FLAG" == "--force" || "${LLM_WIKI_FORCE:-0}" == "1" ]]; then
      export LLM_WIKI_FORCE=1
    fi
    PS1_WIN_PATH="$(to_win_path "$PS1_PATH")"
    if [[ "$INSTALL_SCOPE" == "global" ]]; then
      exec powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PS1_WIN_PATH" -GlobalInstall
    fi
    exec powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PS1_WIN_PATH"
  fi
fi

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
INSTALL_ARGS=()
if [[ "$INSTALL_MODE" == "g-kade" ]]; then
  INSTALLER="$PACKET_ROOT/installers/install_g_kade_workspace.py"
  INSTALL_ARGS=("$INSTALLER" --workspace "$VAULT" --targets "$TARGETS")
else
  INSTALL_ARGS=("$INSTALLER" --vault "$VAULT" --targets "$TARGETS")
fi

if [[ ! -f "$INSTALLER" ]]; then
  echo "Installer not found in downloaded packet: $INSTALLER" >&2
  exit 1
fi

if [[ "$FORCE_FLAG" == "--force" || "${LLM_WIKI_FORCE:-0}" == "1" ]]; then
  INSTALL_ARGS+=(--force)
fi

if [[ "${LLM_WIKI_SKIP_HOME_SKILLS:-0}" == "1" ]]; then
  INSTALL_ARGS+=(--skip-home-skills)
fi
if [[ "$INSTALL_MODE" == "g-kade" && "${LLM_WIKI_SKIP_SETUP:-0}" == "1" ]]; then
  INSTALL_ARGS+=(--skip-setup)
fi

python3 "${INSTALL_ARGS[@]}"

if [[ "$INSTALL_MODE" != "g-kade" && "${LLM_WIKI_SKIP_SETUP:-0}" != "1" ]]; then
  SETUP_HELPER="$VAULT/scripts/setup_llm_wiki_memory.sh"
  if [[ ! -f "$SETUP_HELPER" ]]; then
    echo "Setup helper not found: $SETUP_HELPER" >&2
    exit 1
  fi
  bash "$SETUP_HELPER" --workspace "$VAULT"
fi
