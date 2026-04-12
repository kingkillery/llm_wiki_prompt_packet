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
ENABLE_GITVIZZ="${LLM_WIKI_ENABLE_GITVIZZ:-0}"
GITVIZZ_SOURCE="${LLM_WIKI_GITVIZZ_SOURCE:-/gitvizz-source}"
GITVIZZ_WAIT_TIMEOUT="${LLM_WIKI_GITVIZZ_WAIT_TIMEOUT:-120}"
MCP_UPSTREAM_HOST="${LLM_WIKI_MCP_UPSTREAM_HOST:-127.0.0.1}"

mkdir -p "$VAULT_PATH" "$VAULT_PATH/.brv/context-tree" "$HOME/.claude" "$HOME/.codex" "$HOME/.factory" "$NPM_CONFIG_PREFIX" "$NPM_CONFIG_CACHE"

configure_git_auth() {
  local github_token="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
  if [[ -z "$github_token" ]]; then
    return 0
  fi

  git config --global url."https://${github_token}:x-oauth-basic@github.com/".insteadOf https://github.com/
  git config --global url."https://${github_token}:x-oauth-basic@github.com/".insteadOf ssh://git@github.com/
  git config --global url."https://${github_token}:x-oauth-basic@github.com/".insteadOf git@github.com:
}

gitvizz_source_ready() {
  [[ -d "$GITVIZZ_SOURCE" ]] || return 1
  [[ -f "$GITVIZZ_SOURCE/docker-compose.yaml" || -f "$GITVIZZ_SOURCE/docker-compose.yml" ]]
}

configure_gitvizz_mode() {
  if [[ "$ENABLE_GITVIZZ" != "1" ]]; then
    return 0
  fi

  if [[ -z "${LLM_WIKI_GITVIZZ_FRONTEND_URL:-}" || "${LLM_WIKI_GITVIZZ_FRONTEND_URL:-}" == "http://localhost:3000" || "${LLM_WIKI_GITVIZZ_FRONTEND_URL:-}" == "http://127.0.0.1:3000" ]]; then
    export LLM_WIKI_GITVIZZ_FRONTEND_URL="http://gitvizz-frontend:3000"
  fi

  if [[ -z "${LLM_WIKI_GITVIZZ_BACKEND_URL:-}" || "${LLM_WIKI_GITVIZZ_BACKEND_URL:-}" == "http://localhost:8003" || "${LLM_WIKI_GITVIZZ_BACKEND_URL:-}" == "http://127.0.0.1:8003" ]]; then
    export LLM_WIKI_GITVIZZ_BACKEND_URL="http://gitvizz-backend:8003"
  fi

  if [[ -z "${LLM_WIKI_GITVIZZ_REPO_PATH:-}" ]] && gitvizz_source_ready; then
    export LLM_WIKI_GITVIZZ_REPO_PATH="$GITVIZZ_SOURCE"
  fi

  SKIP_GITVIZZ=0
  export LLM_WIKI_SKIP_GITVIZZ=0
}

wait_for_url() {
  local url="$1"
  local timeout_seconds="$2"

  python3 - "$url" "$timeout_seconds" <<'PY'
import socket
import sys
import time
from urllib.parse import urlparse

url = sys.argv[1]
timeout_seconds = int(sys.argv[2])
parsed = urlparse(url)
host = parsed.hostname
port = parsed.port

if not host or not port:
    raise SystemExit(f"invalid URL: {url}")

deadline = time.time() + timeout_seconds
last_error = None

while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=1.5):
            raise SystemExit(0)
    except OSError as exc:
        last_error = exc
        time.sleep(1)

if last_error is None:
    last_error = RuntimeError("timed out waiting for service")

print(f"Timed out waiting for {url}: {last_error}", file=sys.stderr)
raise SystemExit(1)
PY
}

wait_for_gitvizz() {
  if [[ "$ENABLE_GITVIZZ" != "1" ]]; then
    return 0
  fi

  wait_for_url "${LLM_WIKI_GITVIZZ_FRONTEND_URL:?}" "$GITVIZZ_WAIT_TIMEOUT"
  wait_for_url "${LLM_WIKI_GITVIZZ_BACKEND_URL:?}" "$GITVIZZ_WAIT_TIMEOUT"
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

  if [[ "$ENABLE_GITVIZZ" == "1" ]]; then
    setup_args+=("--skip-gitvizz-start")
  fi

  if [[ "$SKIP_GITVIZZ" == "1" ]]; then
    setup_args+=("--skip-gitvizz")
  fi

  bash "$VAULT_PATH/scripts/setup_llm_wiki_memory.sh" "${setup_args[@]}"
}

run_mcp_server() {
  local default_cmd="pk-qmd mcp"
  if [[ "$MCP_SERVER_CMD" != "$default_cmd" ]]; then
    exec bash -lc "$MCP_SERVER_CMD"
  fi

  local qmd_command=""
  if command -v pk-qmd >/dev/null 2>&1; then
    qmd_command="pk-qmd"
  fi

  local candidates=(
    "$VAULT_PATH/.llm-wiki/pk-qmd-source"
    "$VAULT_PATH/.llm-wiki/node_modules/.bin/pk-qmd"
    "$VAULT_PATH/.llm-wiki/node_modules/.bin/pk-qmd.cmd"
    "$VAULT_PATH/.llm-wiki/node_modules/.bin/pk-qmd.ps1"
  )

  local candidate
  if [[ -z "$qmd_command" ]]; then
    for candidate in "${candidates[@]}"; do
      if [[ -x "$candidate" || -f "$candidate" ]]; then
        qmd_command="$candidate"
        break
      fi
    done
  fi

  if [[ -z "$qmd_command" ]]; then
    echo "Unable to resolve a pk-qmd MCP command after bootstrap." >&2
    exit 1
  fi

  local public_port="${LLM_WIKI_MCP_PUBLIC_PORT:-8181}"
  local upstream_port="${LLM_WIKI_MCP_UPSTREAM_PORT:-18181}"

  "$qmd_command" mcp --http --port "$upstream_port" &
  local qmd_pid=$!

  node /opt/llm-wiki/docker/mcp_http_proxy.mjs "$public_port" "$upstream_port" "$MCP_UPSTREAM_HOST" &
  local proxy_pid=$!

  trap 'kill "$qmd_pid" "$proxy_pid" 2>/dev/null || true' EXIT INT TERM

  while kill -0 "$qmd_pid" >/dev/null 2>&1; do
    if python3 - "$MCP_UPSTREAM_HOST" "$upstream_port" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
try:
    with socket.create_connection((host, port), timeout=0.5):
        raise SystemExit(0)
except OSError:
    raise SystemExit(1)
PY
    then
      break
    fi
    sleep 1
  done

  wait -n "$qmd_pid" "$proxy_pid"
  local exit_code=$?
  kill "$qmd_pid" "$proxy_pid" 2>/dev/null || true
  wait "$qmd_pid" 2>/dev/null || true
  wait "$proxy_pid" 2>/dev/null || true
  return "$exit_code"
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
    configure_gitvizz_mode
    install_packet
    ;;
  bootstrap)
    configure_git_auth
    configure_gitvizz_mode
    stage_qmd_source
    install_packet
    wait_for_gitvizz
    bootstrap_packet
    ;;
  health)
    configure_git_auth
    configure_gitvizz_mode
    stage_qmd_source
    FORCE_INSTALL=1
    install_packet
    wait_for_gitvizz
    health_check
    ;;
  shell)
    exec bash "$@"
    ;;
  serve)
    configure_git_auth
    configure_gitvizz_mode
    stage_qmd_source
    install_packet
    wait_for_gitvizz
    bootstrap_packet
    run_mcp_server
    ;;
  *)
    echo "Unknown entrypoint mode: $MODE" >&2
    exit 1
    ;;
esac
