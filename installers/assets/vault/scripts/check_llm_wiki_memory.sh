#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_PATH="${1:-$(cd "$SCRIPT_DIR/.." && pwd)/.llm-wiki/config.json}"

if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "Stack config not found: $CONFIG_PATH" >&2
  exit 1
fi

mapfile -t CFG < <(python3 - "$CONFIG_PATH" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    cfg = json.load(handle)

print(cfg["pk_qmd"]["command"])
print(cfg["byterover"]["command"])
print(cfg["gitvizz"]["frontend_url"])
print(cfg["gitvizz"]["backend_url"])
print(cfg["pk_qmd"].get("collection_name", ""))
for value in cfg["pk_qmd"].get("local_command_candidates", []):
    print(value)
PY
)

QMD_COMMAND="${CFG[0]}"
BRV_COMMAND="${CFG[1]}"
FRONTEND_URL="${CFG[2]}"
BACKEND_URL="${CFG[3]}"
WORKSPACE_ROOT="$(cd "$(dirname "$CONFIG_PATH")/.." && pwd)"
COLLECTION_NAME="${CFG[4]}"
LOCAL_QMD_COMMAND_CANDIDATES=("${CFG[@]:5}")
if [[ -z "$COLLECTION_NAME" ]]; then
  COLLECTION_NAME="$(basename "$WORKSPACE_ROOT" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')"
fi

resolve_qmd_command() {
  local configured="$1"
  shift
  local candidate

  for candidate in "$@"; do
    if [[ -x "$WORKSPACE_ROOT/$candidate" || -f "$WORKSPACE_ROOT/$candidate" ]]; then
      printf '%s\n' "$WORKSPACE_ROOT/$candidate"
      return 0
    fi
  done

  printf '%s\n' "$configured"
}

QMD_COMMAND="$(resolve_qmd_command "$QMD_COMMAND" "${LOCAL_QMD_COMMAND_CANDIDATES[@]}")"

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

FAILURES=()

echo "=== llm-wiki-memory health check ==="
echo "Config: $CONFIG_PATH"

if ! command -v "$QMD_COMMAND" >/dev/null 2>&1; then
  FAILURES+=("Missing pk-qmd command: $QMD_COMMAND")
else
  echo
  echo "=== pk-qmd ==="
  "$QMD_COMMAND" status || true

  if "$QMD_COMMAND" 2>&1 | grep -q "pk-qmd collection add"; then
    collection_output="$("$QMD_COMMAND" collection list 2>&1 || true)"
    if [[ "$collection_output" != *"$COLLECTION_NAME (qmd://"* ]]; then
      FAILURES+=("Missing qmd collection: $COLLECTION_NAME")
    fi
  else
    echo "Warning: $QMD_COMMAND does not expose collection commands; collection bootstrap could not be verified." >&2
  fi
fi

if ! command -v "$BRV_COMMAND" >/dev/null 2>&1; then
  FAILURES+=("Missing Byterover command: $BRV_COMMAND")
else
  echo
  echo "=== Byterover ==="
  "$BRV_COMMAND" status || true

  if [[ -z "${BYTEROVER_API_KEY:-}" ]]; then
    echo "Warning: BYTEROVER_API_KEY is not set. Login or export the API key before first use." >&2
  fi

  if [[ ! -f "$WORKSPACE_ROOT/.brv/config.json" ]]; then
    FAILURES+=("Missing BRV workspace config: $WORKSPACE_ROOT/.brv/config.json")
  fi
fi

echo
echo "=== GitVizz ==="
echo "Frontend: $FRONTEND_URL"
echo "Backend:  $BACKEND_URL"

if ! check_tcp_url "$FRONTEND_URL"; then
  FAILURES+=("GitVizz frontend is not reachable: $FRONTEND_URL")
fi

if ! check_tcp_url "$BACKEND_URL"; then
  FAILURES+=("GitVizz backend is not reachable: $BACKEND_URL")
fi

if [[ ${#FAILURES[@]} -gt 0 ]]; then
  printf '%s\n' "${FAILURES[@]}" >&2
  exit 1
fi

echo
echo "Health check passed."
