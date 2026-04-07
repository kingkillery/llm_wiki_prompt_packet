#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_PARENT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCRIPT_GRANDPARENT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [[ -f "$SCRIPT_PARENT/.llm-wiki/config.json" ]]; then
  WORKSPACE_ROOT="$SCRIPT_PARENT"
else
  WORKSPACE_ROOT="$SCRIPT_GRANDPARENT"
fi
CONFIG_PATH="$WORKSPACE_ROOT/.llm-wiki/config.json"
QMD_SOURCE="${LLM_WIKI_QMD_SOURCE:-}"
QMD_REPO_URL="${LLM_WIKI_QMD_REPO_URL:-}"
QMD_COMMAND="${LLM_WIKI_QMD_COMMAND:-}"
QMD_COLLECTION="${LLM_WIKI_QMD_COLLECTION:-}"
QMD_CONTEXT="${LLM_WIKI_QMD_CONTEXT:-}"
BRV_COMMAND="${LLM_WIKI_BRV_COMMAND:-}"
GITVIZZ_FRONTEND_URL="${LLM_WIKI_GITVIZZ_FRONTEND_URL:-}"
GITVIZZ_BACKEND_URL="${LLM_WIKI_GITVIZZ_BACKEND_URL:-}"
GITVIZZ_REPO_PATH="${LLM_WIKI_GITVIZZ_REPO_PATH:-}"
SKIP_QMD=0
SKIP_MCP=0
SKIP_QMD_BOOTSTRAP=0
SKIP_QMD_EMBED=0
SKIP_BRV=0
SKIP_BRV_INIT=0
SKIP_GITVIZZ_START=0
VERIFY_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config-path)
      CONFIG_PATH="$2"
      shift 2
      ;;
    --workspace)
      WORKSPACE_ROOT="$2"
      shift 2
      ;;
    --qmd-source)
      QMD_SOURCE="$2"
      shift 2
      ;;
    --qmd-repo-url)
      QMD_REPO_URL="$2"
      shift 2
      ;;
    --qmd-command)
      QMD_COMMAND="$2"
      shift 2
      ;;
    --qmd-collection)
      QMD_COLLECTION="$2"
      shift 2
      ;;
    --qmd-context)
      QMD_CONTEXT="$2"
      shift 2
      ;;
    --brv-command)
      BRV_COMMAND="$2"
      shift 2
      ;;
    --gitvizz-frontend-url)
      GITVIZZ_FRONTEND_URL="$2"
      shift 2
      ;;
    --gitvizz-backend-url)
      GITVIZZ_BACKEND_URL="$2"
      shift 2
      ;;
    --gitvizz-repo-path)
      GITVIZZ_REPO_PATH="$2"
      shift 2
      ;;
    --skip-qmd)
      SKIP_QMD=1
      shift
      ;;
    --skip-mcp)
      SKIP_MCP=1
      shift
      ;;
    --skip-qmd-bootstrap)
      SKIP_QMD_BOOTSTRAP=1
      shift
      ;;
    --skip-qmd-embed)
      SKIP_QMD_EMBED=1
      shift
      ;;
    --skip-brv)
      SKIP_BRV=1
      shift
      ;;
    --skip-brv-init)
      SKIP_BRV_INIT=1
      shift
      ;;
    --skip-gitvizz-start)
      SKIP_GITVIZZ_START=1
      shift
      ;;
    --verify-only)
      VERIFY_ONLY=1
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

mapfile -t CFG < <(python3 - "$CONFIG_PATH" "$WORKSPACE_ROOT" <<'PY'
import json
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
workspace = Path(sys.argv[2])

defaults = [
    "pk-qmd",
    "brv",
    "http://localhost:3000",
    "http://localhost:8003",
    "https://github.com/kingkillery/pk-qmd",
    workspace.name.lower().replace(" ", "-"),
    f"Primary llm-wiki-memory vault for {workspace}",
]

if not config_path.exists():
    for value in defaults:
        print(value)
    raise SystemExit

with config_path.open("r", encoding="utf-8") as handle:
    cfg = json.load(handle)

print(cfg["pk_qmd"]["command"])
print(cfg["byterover"]["command"])
print(cfg["gitvizz"]["frontend_url"])
print(cfg["gitvizz"]["backend_url"])
print(cfg["pk_qmd"]["repo_url"])
print(cfg["pk_qmd"].get("collection_name", workspace.name.lower().replace(" ", "-")))
print(cfg["pk_qmd"].get("context", f"Primary llm-wiki-memory vault for {workspace}"))
print(cfg["gitvizz"].get("repo_path", "") or "")
for value in cfg["pk_qmd"].get("local_command_candidates", []):
    print(value)
PY
)

QMD_COMMAND="${QMD_COMMAND:-${CFG[0]}}"
BRV_COMMAND="${BRV_COMMAND:-${CFG[1]}}"
GITVIZZ_FRONTEND_URL="${GITVIZZ_FRONTEND_URL:-${CFG[2]}}"
GITVIZZ_BACKEND_URL="${GITVIZZ_BACKEND_URL:-${CFG[3]}}"
QMD_REPO_URL="${QMD_REPO_URL:-${CFG[4]}}"
QMD_COLLECTION="${QMD_COLLECTION:-${CFG[5]}}"
QMD_CONTEXT="${QMD_CONTEXT:-${CFG[6]}}"
GITVIZZ_REPO_PATH="${GITVIZZ_REPO_PATH:-${CFG[7]}}"
LOCAL_QMD_COMMAND_CANDIDATES=("${CFG[@]:8}")

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

local_qmd_manifest_path() {
  printf '%s\n' "$WORKSPACE_ROOT/.llm-wiki/package.json"
}

local_qmd_command_path() {
  local candidates=()
  if [[ ${#LOCAL_QMD_COMMAND_CANDIDATES[@]} -gt 0 ]]; then
    candidates=("${LOCAL_QMD_COMMAND_CANDIDATES[@]}")
  else
    candidates=(
      ".llm-wiki/node_modules/.bin/pk-qmd"
      ".llm-wiki/node_modules/.bin/pk-qmd.cmd"
      ".llm-wiki/node_modules/.bin/pk-qmd.ps1"
    )
  fi

  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -x "$WORKSPACE_ROOT/$candidate" || -f "$WORKSPACE_ROOT/$candidate" ]]; then
      printf '%s\n' "$WORKSPACE_ROOT/$candidate"
      return 0
    fi
  done
  return 1
}

resolve_git_source() {
  local repo_url="$1"
  if [[ "$repo_url" == git+* ]]; then
    printf '%s\n' "$repo_url"
  elif [[ "$repo_url" == *.git ]]; then
    printf 'git+%s\n' "$repo_url"
  else
    printf 'git+%s.git\n' "$repo_url"
  fi
}

test_qmd_feature() {
  local command_name="$1"
  local pattern="$2"
  local output
  output="$("$command_name" 2>&1 || true)"
  [[ "$output" == *"$pattern"* ]]
}

patch_json_config() {
  local target="$1"
  local mode="$2"
  local command_name="$3"
  python3 - "$target" "$mode" "$command_name" <<'PY'
from pathlib import Path
import json
import sys

path = Path(sys.argv[1]).expanduser()
mode = sys.argv[2]
command_name = sys.argv[3]

data = {}
if path.exists():
    raw = path.read_text(encoding="utf-8").strip()
    if raw:
        data = json.loads(raw)

mcp = data.get("mcpServers")
if not isinstance(mcp, dict):
    mcp = {}
data["mcpServers"] = mcp

payload = {"command": command_name, "args": ["mcp"]}
if mode == "factory":
    payload = {"type": "stdio", "command": command_name, "args": ["mcp"], "disabled": False}

mcp["pk-qmd"] = payload
mcp.pop("qmd", None)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
}

patch_codex_toml() {
  local target="$1"
  local command_name="$2"
  python3 - "$target" "$command_name" <<'PY'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1]).expanduser()
command_name = sys.argv[2]
content = path.read_text(encoding="utf-8") if path.exists() else ""
block = f'[mcp_servers.pk-qmd]\ncommand = "{command_name}"\nargs = ["mcp"]\n'
section = re.compile(r'(?ms)^\[mcp_servers\.pk-qmd\]\n(?:.*?)(?=^\[|\Z)')
legacy = re.compile(r'(?ms)^\[mcp_servers\.qmd\]\n(?:.*?)(?=^\[|\Z)')

if section.search(content):
    content = section.sub(block + "\n", content)
else:
    if content and not content.endswith("\n"):
        content += "\n"
    content += "\n" + block + "\n"

content = legacy.sub("", content)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(content, encoding="utf-8")
PY
}

check_tcp_url() {
  python3 - "$1" <<'PY'
import socket
import sys
from urllib.parse import urlparse

url = urlparse(sys.argv[1])
port = url.port or (443 if url.scheme == "https" else 80)
sock = socket.create_connection((url.hostname, port), timeout=3)
sock.close()
PY
}

start_gitvizz_if_needed() {
  if check_tcp_url "$GITVIZZ_FRONTEND_URL" && check_tcp_url "$GITVIZZ_BACKEND_URL"; then
    SUMMARY+=("GitVizz already reachable")
    return 0
  fi

  if [[ "$VERIFY_ONLY" -eq 1 ]]; then
    SUMMARY+=("GitVizz is not reachable")
    return 0
  fi

  if [[ -z "$GITVIZZ_REPO_PATH" ]]; then
    SUMMARY+=("GitVizz repo path not configured; set LLM_WIKI_GITVIZZ_REPO_PATH or gitvizz.repo_path to auto-launch")
    return 0
  fi

  if [[ ! -f "$GITVIZZ_REPO_PATH/docker-compose.yaml" ]]; then
    SUMMARY+=("GitVizz repo path missing docker-compose.yaml: $GITVIZZ_REPO_PATH")
    return 0
  fi

  (
    cd "$GITVIZZ_REPO_PATH"
    docker-compose up -d --build
  )

  if check_tcp_url "$GITVIZZ_FRONTEND_URL" && check_tcp_url "$GITVIZZ_BACKEND_URL"; then
    SUMMARY+=("Launched GitVizz via docker-compose")
  else
    SUMMARY+=("GitVizz launch attempted but endpoints are still unreachable")
  fi
}

install_packet_local_qmd_dependency() {
  local manifest
  manifest="$(local_qmd_manifest_path)"
  if [[ ! -f "$manifest" ]]; then
    return 1
  fi
  require_cmd npm
  npm install --prefix "$(dirname "$manifest")"
  local_qmd_command_path
}

ensure_qmd_available() {
  if local_cmd="$(local_qmd_command_path 2>/dev/null)"; then
    QMD_COMMAND="$local_cmd"
    QMD_SOURCE_RESULT="packet-local-existing"
    return 0
  fi

  if command -v "$QMD_COMMAND" >/dev/null 2>&1; then
    QMD_SOURCE_RESULT="existing"
    return 0
  fi

  if [[ "$VERIFY_ONLY" -eq 1 ]]; then
    QMD_SOURCE_RESULT="missing"
    return 1
  fi

  if [[ -n "$QMD_SOURCE" ]]; then
    require_cmd npm
    npm install -g "$QMD_SOURCE"
    QMD_SOURCE_RESULT="$QMD_SOURCE"
    return 0
  fi

  if local_cmd="$(install_packet_local_qmd_dependency 2>/dev/null)"; then
    QMD_COMMAND="$local_cmd"
    QMD_SOURCE_RESULT="packet-local"
    return 0
  fi

  require_cmd npm
  local git_source
  git_source="$(resolve_git_source "$QMD_REPO_URL")"
  npm install -g "$git_source"
  QMD_SOURCE_RESULT="$git_source"
  return 0
}

qmd_collection_bootstrap() {
  if ! test_qmd_feature "$QMD_COMMAND" "collection add"; then
    SUMMARY+=("$QMD_COMMAND does not expose collection commands. Install the richer pk-qmd fork before bootstrapping the vault.")
    return
  fi

  local collection_output
  collection_output="$("$QMD_COMMAND" collection list 2>&1 || true)"

  if [[ "$collection_output" != *"$QMD_COLLECTION (qmd://"* ]]; then
    if [[ "$VERIFY_ONLY" -eq 1 ]]; then
      FAILURES+=("Missing qmd collection: $QMD_COLLECTION")
      return
    fi
    "$QMD_COMMAND" collection add "$WORKSPACE_ROOT" --name "$QMD_COLLECTION"
    SUMMARY+=("Added qmd collection: $QMD_COLLECTION")
  else
    SUMMARY+=("qmd collection already present: $QMD_COLLECTION")
  fi

  local context_output
  context_output="$("$QMD_COMMAND" context list 2>&1 || true)"
  local context_path="qmd://$QMD_COLLECTION/"
  if [[ -n "$QMD_CONTEXT" && "$context_output" != *"$context_path"* ]]; then
    if [[ "$VERIFY_ONLY" -eq 1 ]]; then
      FAILURES+=("Missing qmd context: $context_path")
    else
      "$QMD_COMMAND" context add "$context_path" "$QMD_CONTEXT"
      SUMMARY+=("Added qmd context: $context_path")
    fi
  elif [[ -n "$QMD_CONTEXT" ]]; then
    SUMMARY+=("qmd context already present: $context_path")
  fi

  if [[ "$VERIFY_ONLY" -eq 0 ]]; then
    local runner="$WORKSPACE_ROOT/scripts/qmd_embed_runner.mjs"
    if command -v node >/dev/null 2>&1 && [[ -f "$runner" ]]; then
      local runner_args=("$runner" "--workspace" "$WORKSPACE_ROOT" "--collection" "$QMD_COLLECTION")
      if [[ "$SKIP_QMD_EMBED" -eq 1 ]]; then
        runner_args+=("--skip-text" "--skip-update")
      elif [[ -n "${GEMINI_API_KEY:-}" ]]; then
        runner_args+=("--include-images")
      fi
      node "${runner_args[@]}"
      SUMMARY+=("Ran qmd embed runner")
    elif [[ "$SKIP_QMD_EMBED" -eq 0 ]]; then
      "$QMD_COMMAND" update
      "$QMD_COMMAND" embed
      if [[ -n "${GEMINI_API_KEY:-}" ]] && test_qmd_feature "$QMD_COMMAND" "membed"; then
        "$QMD_COMMAND" membed
        SUMMARY+=("Ran qmd text + image embeddings")
      else
        SUMMARY+=("Ran qmd text embeddings")
      fi
    fi
  fi
}

init_brv_workspace() {
  local brv_config="$WORKSPACE_ROOT/.brv/config.json"
  if [[ -f "$brv_config" ]]; then
    SUMMARY+=("BRV workspace already initialized")
    return
  fi

  if [[ "$VERIFY_ONLY" -eq 1 ]]; then
    FAILURES+=("Missing BRV workspace config: $brv_config")
    return
  fi

  (
    cd "$WORKSPACE_ROOT"
    "$BRV_COMMAND" init
  )

  if [[ -f "$brv_config" ]]; then
    SUMMARY+=("Initialized BRV workspace")
  else
    SUMMARY+=("BRV init ran but no config was created at $brv_config")
  fi
}

test_brv_status() {
  local output
  if output="$("$BRV_COMMAND" status --format json 2>&1)"; then
    printf '%s\n' "$output"
    return 0
  fi
  printf '%s\n' "$output" >&2
  return 1
}

get_brv_providers() {
  "$BRV_COMMAND" providers list --format json 2>/dev/null || true
}

SUMMARY=()
FAILURES=()

if [[ "$SKIP_QMD" -eq 0 ]]; then
  if ensure_qmd_available; then
    case "${QMD_SOURCE_RESULT:-existing}" in
      existing)
        SUMMARY+=("$QMD_COMMAND already installed")
        ;;
      packet-local-existing)
        SUMMARY+=("Using packet-local pk-qmd dependency at $QMD_COMMAND")
        ;;
      packet-local)
        SUMMARY+=("Installed packet-local pk-qmd dependency into .llm-wiki")
        ;;
      *)
        SUMMARY+=("Installed pk-qmd from ${QMD_SOURCE_RESULT}")
        ;;
    esac

    if "$QMD_COMMAND" status; then
      SUMMARY+=("pk-qmd verify: ok")
    else
      FAILURES+=("pk-qmd status failed for: $QMD_COMMAND")
    fi

    if [[ "$SKIP_MCP" -eq 0 && ${#FAILURES[@]} -eq 0 ]]; then
      require_cmd python3
      patch_json_config "$HOME/.claude/settings.json" claude "$QMD_COMMAND"
      SUMMARY+=("Updated ~/.claude/settings.json")
      patch_codex_toml "$HOME/.codex/config.toml" "$QMD_COMMAND"
      SUMMARY+=("Updated ~/.codex/config.toml")
      patch_json_config "$HOME/.factory/mcp.json" factory "$QMD_COMMAND"
      SUMMARY+=("Updated ~/.factory/mcp.json")
    fi

    if [[ "$SKIP_QMD_BOOTSTRAP" -eq 0 && ${#FAILURES[@]} -eq 0 ]]; then
      qmd_collection_bootstrap
    fi
  else
    FAILURES+=("Missing pk-qmd command: $QMD_COMMAND")
    SUMMARY+=("Install pk-qmd from the packet dependency manifest, $QMD_REPO_URL, or provide --qmd-source")
  fi
fi

if [[ "$SKIP_BRV" -eq 0 ]]; then
  if command -v "$BRV_COMMAND" >/dev/null 2>&1; then
    SUMMARY+=("$BRV_COMMAND already installed")
  elif [[ "$VERIFY_ONLY" -eq 1 ]]; then
    FAILURES+=("Missing Byterover command: $BRV_COMMAND")
  else
    require_cmd npm
    npm install -g byterover-cli
    SUMMARY+=("Installed brv from npm")
  fi

  if command -v "$BRV_COMMAND" >/dev/null 2>&1; then
    if test_brv_status >/dev/null; then
      SUMMARY+=("brv verify: ok")
    else
      FAILURES+=("brv status failed for: $BRV_COMMAND")
    fi

    providers_json="$(get_brv_providers)"
    if [[ -n "$providers_json" ]] && python3 - "$providers_json" <<'PY'
import json
import sys
data = json.loads(sys.argv[1])
providers = data.get("data", {}).get("providers", [])
connected = next((p for p in providers if p.get("isConnected")), None)
if connected:
    print(connected.get("id", "unknown"))
PY
    then
      connected_provider="$(python3 - "$providers_json" <<'PY'
import json
import sys
data = json.loads(sys.argv[1])
providers = data.get("data", {}).get("providers", [])
connected = next((p for p in providers if p.get("isConnected")), None)
print(connected.get("id", "")) if connected else print("")
PY
)"
      if [[ -n "$connected_provider" ]]; then
        SUMMARY+=("brv provider connected: $connected_provider")
      fi
    fi
    if [[ "${connected_provider:-}" == "" ]]; then
      SUMMARY+=("Next BRV steps: connect a provider before using brv_query/brv_curate, e.g. 'brv providers connect byterover' or another supported provider")
    fi
    if [[ -z "${BYTEROVER_API_KEY:-}" ]]; then
      SUMMARY+=("Optional BRV cloud auth: brv login --api-key <key> or export BYTEROVER_API_KEY")
    fi

    if [[ "$SKIP_BRV_INIT" -eq 0 ]]; then
      init_brv_workspace
    fi
  fi
fi

if [[ "$SKIP_GITVIZZ_START" -eq 0 ]]; then
  start_gitvizz_if_needed
fi

if check_tcp_url "$GITVIZZ_FRONTEND_URL"; then
  SUMMARY+=("GitVizz frontend reachable: $GITVIZZ_FRONTEND_URL")
else
  FAILURES+=("GitVizz frontend unreachable: $GITVIZZ_FRONTEND_URL")
fi

if check_tcp_url "$GITVIZZ_BACKEND_URL"; then
  SUMMARY+=("GitVizz backend reachable: $GITVIZZ_BACKEND_URL")
else
  FAILURES+=("GitVizz backend unreachable: $GITVIZZ_BACKEND_URL")
fi

printf '%s\n' "${SUMMARY[@]}"

if [[ ${#FAILURES[@]} -gt 0 ]]; then
  printf '%s\n' "${FAILURES[@]}" >&2
  exit 1
fi
