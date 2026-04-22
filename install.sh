#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
llm_wiki_prompt_packet installer

Usage:
  install.sh [VAULT] [TARGETS] [--force] [REF]
  install.sh --wire-repo [--vault PATH] [--force]
  install.sh --mode {packet|g-kade} [other flags]

Modes:
  packet   (default) Install the packet into a vault folder. The vault is the
           Obsidian-style knowledge directory; the agent reads/writes notes here.
  g-kade   Wire the packet into a target repo as a workspace, mounting the
           harness skill surfaces (kade-hq, gstack, g-kade) into the project.

Convenience:
  --wire-repo         Shorthand for --mode g-kade with the current directory as
                      the project root and --global-wire enabled. This is the
                      one-command path for "wire this packet into the repo I'm in".
  --global-wire       After install, write the LLM Wiki section into
                      ~/.claude/CLAUDE.md and copy wiki-*.md commands into
                      ~/.claude/commands/. Default-on for --wire-repo.
  --no-global-wire    Disable global Claude wiring even with --wire-repo.
  -g | --global-install   Install scope: global (vs default local).

Environment overrides (CLI flags win):
  LLM_WIKI_INSTALL_MODE   packet | g-kade
  LLM_WIKI_VAULT          Vault path (packet mode) or project root (g-kade)
  LLM_WIKI_TARGETS        Comma-separated agent targets
  LLM_WIKI_REF            Git ref to fetch (default: main)
  LLM_WIKI_FORCE          1 = --force
  LLM_WIKI_GLOBAL_WIRE    1 = enable global Claude wiring
  LLM_WIKI_SKIP_SETUP     1 = skip running setup helper after install
  LLM_WIKI_SKIP_HOME_SKILLS  1 = pass --skip-home-skills to installer
USAGE
}

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
INSTALL_MODE="${LLM_WIKI_INSTALL_MODE:-packet}"
WIRE_REPO=0
GLOBAL_WIRE_FLAG=""   # "", "1", or "0" — empty means "use default for mode"
EXPLICIT_VAULT=""

POSITIONAL=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    -g|--global-install)
      INSTALL_SCOPE="global"
      shift
      ;;
    --local-install)
      INSTALL_SCOPE="local"
      shift
      ;;
    --mode)
      if [[ $# -lt 2 ]]; then
        echo "--mode requires a value (packet|g-kade)" >&2
        exit 2
      fi
      INSTALL_MODE="$2"
      shift 2
      ;;
    --mode=*)
      INSTALL_MODE="${1#--mode=}"
      shift
      ;;
    --wire-repo)
      WIRE_REPO=1
      INSTALL_MODE="g-kade"
      shift
      ;;
    --vault)
      if [[ $# -lt 2 ]]; then
        echo "--vault requires a value" >&2
        exit 2
      fi
      EXPLICIT_VAULT="$2"
      shift 2
      ;;
    --vault=*)
      EXPLICIT_VAULT="${1#--vault=}"
      shift
      ;;
    --global-wire)
      GLOBAL_WIRE_FLAG="1"
      shift
      ;;
    --no-global-wire)
      GLOBAL_WIRE_FLAG="0"
      shift
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done
set -- "${POSITIONAL[@]}"

case "$INSTALL_MODE" in
  packet|g-kade) ;;
  *)
    echo "Unknown --mode '$INSTALL_MODE' (expected: packet | g-kade)" >&2
    exit 2
    ;;
esac

VAULT="${EXPLICIT_VAULT:-${1:-${LLM_WIKI_VAULT:-}}}"
TARGETS="${2:-${LLM_WIKI_TARGETS:-claude,antigravity,codex,droid,pi}}"
FORCE_FLAG="${3:-}"
REF="${4:-${LLM_WIKI_REF:-main}}"
REPO="kingkillery/llm_wiki_prompt_packet"
export LLM_WIKI_INSTALL_SCOPE="$INSTALL_SCOPE"
export LLM_WIKI_INSTALL_MODE="$INSTALL_MODE"

# Wire-repo defaults: vault = current dir, global-wire on unless explicitly disabled.
if [[ "$WIRE_REPO" == "1" ]]; then
  if [[ -z "$VAULT" ]]; then
    VAULT="$PWD"
  fi
  if [[ -z "$GLOBAL_WIRE_FLAG" ]]; then
    GLOBAL_WIRE_FLAG="1"
  fi
fi

# Resolve global-wire to 0/1.
if [[ -z "$GLOBAL_WIRE_FLAG" ]]; then
  GLOBAL_WIRE_FLAG="${LLM_WIKI_GLOBAL_WIRE:-0}"
fi

if (is_windows_bash || is_wsl) && command -v powershell.exe >/dev/null 2>&1; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  PS1_PATH="$SCRIPT_DIR/install.ps1"
  if [[ -f "$PS1_PATH" ]]; then
    export LLM_WIKI_VAULT="$(to_win_path "${VAULT:-$PWD}")"
    export LLM_WIKI_TARGETS="$TARGETS"
    export LLM_WIKI_REF="$REF"
    export LLM_WIKI_INSTALL_MODE="$INSTALL_MODE"
    export LLM_WIKI_GLOBAL_WIRE="$GLOBAL_WIRE_FLAG"
    if [[ "$FORCE_FLAG" == "--force" || "${LLM_WIKI_FORCE:-0}" == "1" ]]; then
      export LLM_WIKI_FORCE=1
    fi
    PS1_WIN_PATH="$(to_win_path "$PS1_PATH")"
    PS1_ARGS=(-NoProfile -ExecutionPolicy Bypass -File "$PS1_WIN_PATH")
    if [[ "$INSTALL_SCOPE" == "global" ]]; then
      PS1_ARGS+=(-GlobalInstall)
    fi
    if [[ "$WIRE_REPO" == "1" ]]; then
      PS1_ARGS+=(-WireRepo)
    fi
    if [[ "$GLOBAL_WIRE_FLAG" == "1" ]]; then
      PS1_ARGS+=(-GlobalWire)
    elif [[ "$GLOBAL_WIRE_FLAG" == "0" ]]; then
      PS1_ARGS+=(-NoGlobalWire)
    fi
    exec powershell.exe "${PS1_ARGS[@]}"
  fi
fi

if [[ -z "$VAULT" ]]; then
  if [[ -r /dev/tty ]]; then
    exec 3</dev/tty
    if [[ "$INSTALL_MODE" == "g-kade" ]]; then
      read -r -p "Project root to wire [current directory]: " VAULT <&3
    else
      read -r -p "Vault folder to index [current directory]: " VAULT <&3
    fi
  fi
  VAULT="${VAULT:-$PWD}"
fi

if [[ ! -d "$VAULT" ]]; then
  echo "Target does not exist: $VAULT" >&2
  exit 1
fi

VAULT="$(cd "$VAULT" && pwd -P)"

target_label="vault"
if [[ "$INSTALL_MODE" == "g-kade" ]]; then target_label="project"; fi
echo ">> llm_wiki_prompt_packet install"
echo ">>   mode        = $INSTALL_MODE"
echo ">>   $target_label     = $VAULT"
echo ">>   targets     = $TARGETS"
echo ">>   ref         = $REF"
echo ">>   scope       = $INSTALL_SCOPE"
echo ">>   global-wire = $([[ "$GLOBAL_WIRE_FLAG" == "1" ]] && echo on || echo off)"

TMP_DIR="$(mktemp -d)"

# Preflight: detect missing required tools BEFORE network fetch and any state changes.
# A local checkout's preflight.py is preferred so users running install.sh from a clone
# get the check before download. Otherwise we run it after extraction below.
SCRIPT_DIR_LOCAL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_PREFLIGHT="$SCRIPT_DIR_LOCAL/installers/preflight.py"
if [[ "${LLM_WIKI_SKIP_PREFLIGHT:-0}" != "1" && -f "$LOCAL_PREFLIGHT" ]]; then
  if ! python3 "$LOCAL_PREFLIGHT" --mode "$INSTALL_MODE"; then
    echo "preflight failed - re-run after installing the listed tools, or set LLM_WIKI_SKIP_PREFLIGHT=1 to bypass." >&2
    exit 1
  fi
fi
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

# Fallback preflight for piped installs (curl | bash) where the local checkout
# branch above could not find a preflight.py. We have only created a temp dir
# at this point - failing here is safe and reverts via the cleanup trap.
EXTRACTED_PREFLIGHT="$PACKET_ROOT/installers/preflight.py"
if [[ "${LLM_WIKI_SKIP_PREFLIGHT:-0}" != "1" && ! -f "$LOCAL_PREFLIGHT" && -f "$EXTRACTED_PREFLIGHT" ]]; then
  if ! python3 "$EXTRACTED_PREFLIGHT" --mode "$INSTALL_MODE"; then
    echo "preflight failed - re-run after installing the listed tools, or set LLM_WIKI_SKIP_PREFLIGHT=1 to bypass." >&2
    exit 1
  fi
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

# Global Claude wiring — automates the README "Agent Easy Install" steps.
if [[ "$GLOBAL_WIRE_FLAG" == "1" ]]; then
  WIRE_HELPER="$PACKET_ROOT/installers/wire_global_claude.py"
  if [[ -f "$WIRE_HELPER" ]]; then
    echo ">> wiring global Claude config (~/.claude/CLAUDE.md, ~/.claude/commands/)"
    python3 "$WIRE_HELPER" --vault "$VAULT" || echo "warn: global Claude wiring exited non-zero" >&2
  else
    echo "warn: wire_global_claude.py not found in packet; skipping global wire" >&2
  fi
fi

# Closing health check (wire-repo path) so the user sees green/red, not just installer logs.
# Exit code propagates so chained commands (install.sh --wire-repo && next_thing) honor failure.
# Set LLM_WIKI_HEALTH_CHECK_NONFATAL=1 to keep the warn-only behavior.
if [[ "$WIRE_REPO" == "1" || "${LLM_WIKI_RUN_HEALTH_CHECK:-0}" == "1" ]]; then
  CHECK_HELPER="$VAULT/scripts/check_llm_wiki_memory.sh"
  if [[ -f "$CHECK_HELPER" ]]; then
    echo ">> running health check"
    # Capture exit code BEFORE any compound conditional ($? would otherwise
    # reflect the conditional's own evaluation, not the underlying command).
    set +e
    bash "$CHECK_HELPER"
    HEALTH_RC=$?
    set -e
    if [[ "$HEALTH_RC" -ne 0 ]]; then
      if [[ "${LLM_WIKI_HEALTH_CHECK_NONFATAL:-0}" == "1" ]]; then
        echo "warn: health check reported issues (exit $HEALTH_RC; LLM_WIKI_HEALTH_CHECK_NONFATAL=1, continuing)" >&2
      else
        echo "error: health check failed (exit $HEALTH_RC); set LLM_WIKI_HEALTH_CHECK_NONFATAL=1 to ignore" >&2
        exit "$HEALTH_RC"
      fi
    fi
  else
    echo "warn: health check not found at $CHECK_HELPER" >&2
  fi
fi
