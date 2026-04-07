#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-serve}"
if [[ $# -gt 0 ]]; then
  shift
fi

APP_ROOT="/opt/llm-wiki"
VAULT_PATH="${LLM_WIKI_VAULT:-/workspace}"
TARGETS="${LLM_WIKI_TARGETS:-claude,codex,droid}"
FORCE_INSTALL="${LLM_WIKI_FORCE_INSTALL:-0}"
SKIP_GITVIZZ="${LLM_WIKI_SKIP_GITVIZZ:-1}"
MCP_SERVER_CMD="${LLM_WIKI_MCP_SERVER_CMD:-pk-qmd mcp}"

mkdir -p "$VAULT_PATH" "$HOME/.claude" "$HOME/.codex" "$HOME/.factory" "$NPM_CONFIG_PREFIX" "$NPM_CONFIG_CACHE"

configure_git_auth() {
  local github_token="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
  if [[ -z "$github_token" ]]; then
    return 0
  fi

  git config --global url."https://${github_token}:x-oauth-basic@github.com/".insteadOf https://github.com/
  git config --global url."https://${github_token}:x-oauth-basic@github.com/".insteadOf ssh://git@github.com/
  git config --global url."https://${github_token}:x-oauth-basic@github.com/".insteadOf git@github.com:
}

stage_qmd_source() {
  if [[ -z "${LLM_WIKI_QMD_SOURCE:-}" || ! -d "${LLM_WIKI_QMD_SOURCE}" ]]; then
    return 0
  fi

  local staged="/tmp/pk-qmd-source"
  rm -rf "$staged"

  python3 - "$LLM_WIKI_QMD_SOURCE" "$staged" <<'PY'
import os
import shutil
import sys

src = sys.argv[1]
dst = sys.argv[2]

ignore = shutil.ignore_patterns(
    "node_modules",
    ".git",
    ".turbo",
    ".next",
    "coverage",
    "__pycache__",
)

shutil.copytree(src, dst, ignore=ignore)
PY

  npm install --prefix "$staged"
  export LLM_WIKI_QMD_SOURCE="$staged"
}

install_packet() {
  local install_args=(
    "$APP_ROOT/installers/install_obsidian_agent_memory.py"
    "--vault" "$VAULT_PATH"
    "--targets" "$TARGETS"
  )

  if [[ "$FORCE_INSTALL" == "1" ]]; then
    install_args+=("--force")
  fi

  python3 "${install_args[@]}"
}

bootstrap_packet() {
  local setup_args=()

  if [[ -n "${LLM_WIKI_QMD_SOURCE:-}" ]]; then
    setup_args+=("--qmd-source" "$LLM_WIKI_QMD_SOURCE")
  fi

  if [[ "$SKIP_GITVIZZ" == "1" ]]; then
    setup_args+=("--skip-gitvizz")
  fi

  bash "$VAULT_PATH/scripts/setup_llm_wiki_memory.sh" "${setup_args[@]}"
}

health_check() {
  local health_args=()

  if [[ "$SKIP_GITVIZZ" == "1" ]]; then
    health_args+=("--skip-gitvizz")
  fi

  health_args+=("$VAULT_PATH/.llm-wiki/config.json")
  bash "$APP_ROOT/installers/assets/vault/scripts/check_llm_wiki_memory.sh" "${health_args[@]}"
}

case "$MODE" in
  init)
    configure_git_auth
    install_packet
    ;;
  bootstrap)
    configure_git_auth
    stage_qmd_source
    install_packet
    bootstrap_packet
    ;;
  health)
    configure_git_auth
    stage_qmd_source
    FORCE_INSTALL=1
    install_packet
    health_check
    ;;
  shell)
    exec bash "$@"
    ;;
  serve)
    configure_git_auth
    stage_qmd_source
    install_packet
    bootstrap_packet
    exec bash -lc "$MCP_SERVER_CMD"
    ;;
  *)
    echo "Unknown entrypoint mode: $MODE" >&2
    exit 1
    ;;
esac
