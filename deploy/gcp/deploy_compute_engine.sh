#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd gcloud
require_cmd docker
require_cmd python3

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
if [[ -z "$PROJECT_ID" ]]; then
  echo "Set PROJECT_ID or configure a default gcloud project before deploying." >&2
  exit 1
fi

REGION="${REGION:-us-central1}"
ZONE="${ZONE:-${REGION}-a}"
REPOSITORY_NAME="${REPOSITORY_NAME:-llm-wiki}"
IMAGE_NAME="${IMAGE_NAME:-llm-wiki-prompt-packet}"
IMAGE_TAG="${IMAGE_TAG:-$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)}"
IMAGE_URI="${IMAGE_URI:-${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY_NAME}/${IMAGE_NAME}:${IMAGE_TAG}}"
INSTANCE_NAME="${INSTANCE_NAME:-llm-wiki-packet}"
INSTANCE_TAG="${INSTANCE_TAG:-llm-wiki-mcp}"
MACHINE_TYPE="${MACHINE_TYPE:-e2-standard-2}"
SKIP_BUILD="${SKIP_BUILD:-0}"
BOOT_DISK_SIZE_GB="${BOOT_DISK_SIZE_GB:-50}"
IMAGE_FAMILY="${IMAGE_FAMILY:-ubuntu-2404-lts-amd64}"
IMAGE_PROJECT="${IMAGE_PROJECT:-ubuntu-os-cloud}"
PUBLIC_MCP_FIREWALL_RULE="${PUBLIC_MCP_FIREWALL_RULE:-${FIREWALL_RULE:-allow-llm-wiki-mcp}}"
PUBLIC_MCP_SOURCE_RANGES="${PUBLIC_MCP_SOURCE_RANGES:-${SOURCE_RANGES:-}}"
OPEN_PUBLIC_MCP="${OPEN_PUBLIC_MCP:-0}"
REMOTE_DEPLOY_DIR="${REMOTE_DEPLOY_DIR:-/opt/llm-wiki-deploy}"
REMOTE_VAULT_DIR="${REMOTE_VAULT_DIR:-/srv/llm-wiki/vault}"
REMOTE_HOME_DIR="${REMOTE_HOME_DIR:-/srv/llm-wiki/home}"
REMOTE_QMD_SOURCE_DIR="${REMOTE_QMD_SOURCE_DIR:-/srv/llm-wiki/pk-qmd-source}"
REMOTE_GITVIZZ_SOURCE_DIR="${REMOTE_GITVIZZ_SOURCE_DIR:-/srv/llm-wiki/gitvizz-source}"
MCP_PORT="${LLM_WIKI_MCP_PORT:-8181}"
MCP_BIND_HOST="${LLM_WIKI_MCP_BIND_HOST:-127.0.0.1}"
TARGETS="${LLM_WIKI_TARGETS:-claude,codex,droid}"
FORCE_INSTALL="${LLM_WIKI_FORCE_INSTALL:-0}"
SKIP_GITVIZZ="${LLM_WIKI_SKIP_GITVIZZ:-1}"
ENABLE_GITVIZZ="${LLM_WIKI_ENABLE_GITVIZZ:-0}"
GITVIZZ_SOURCE="${LLM_WIKI_GITVIZZ_SOURCE:-/gitvizz-source}"
GITVIZZ_REPO_URL="${LLM_WIKI_GITVIZZ_REPO_URL:-}"
GITVIZZ_CHECKOUT_PATH="${LLM_WIKI_GITVIZZ_CHECKOUT_PATH:-}"
GITVIZZ_REPO_PATH="${LLM_WIKI_GITVIZZ_REPO_PATH:-}"
GITVIZZ_FRONTEND_URL="${LLM_WIKI_GITVIZZ_FRONTEND_URL:-}"
GITVIZZ_BACKEND_URL="${LLM_WIKI_GITVIZZ_BACKEND_URL:-}"
GITVIZZ_WAIT_TIMEOUT="${LLM_WIKI_GITVIZZ_WAIT_TIMEOUT:-120}"
GITVIZZ_MONGO_URI="${LLM_WIKI_GITVIZZ_MONGO_URI:-}"
GITVIZZ_PHOENIX_ENDPOINT="${LLM_WIKI_GITVIZZ_PHOENIX_ENDPOINT:-}"
GITVIZZ_PHOENIX_PROJECT_NAME="${LLM_WIKI_GITVIZZ_PHOENIX_PROJECT_NAME:-}"
QMD_REPO_URL="${LLM_WIKI_QMD_REPO_URL:-https://github.com/kingkillery/pk-qmd}"
QMD_MCP_URL="${LLM_WIKI_QMD_MCP_URL:-}"
BRV_COMMAND="${LLM_WIKI_BRV_COMMAND:-brv}"
MCP_SERVER_CMD="${LLM_WIKI_MCP_SERVER_CMD:-pk-qmd mcp}"
MCP_UPSTREAM_HOST="${LLM_WIKI_MCP_UPSTREAM_HOST:-127.0.0.1}"
AGENT_API_TOKEN="${LLM_WIKI_AGENT_API_TOKEN:-}"
REMOTE_QMD_SOURCE="${GCE_LLM_WIKI_QMD_SOURCE:-}"
LOCAL_QMD_SOURCE="${LLM_WIKI_QMD_SOURCE:-}"
REMOTE_GITVIZZ_SOURCE="${GCE_LLM_WIKI_GITVIZZ_SOURCE:-}"
LOCAL_GITVIZZ_SOURCE="${LLM_WIKI_GITVIZZ_SOURCE_HOST_PATH:-}"
GITVIZZ_BIND_HOST="${LLM_WIKI_GITVIZZ_BIND_HOST:-127.0.0.1}"
BYTEROVER_API_KEY="${BYTEROVER_API_KEY:-}"
OPENAI_API_KEY="${OPENAI_API_KEY:-}"
ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
GROQ_API_KEY="${GROQ_API_KEY:-}"
GEMINI_API_KEY="${GEMINI_API_KEY:-}"
GH_TOKEN="${GH_TOKEN:-}"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

USE_LOCAL_QMD_SOURCE=0
if [[ -n "$LOCAL_QMD_SOURCE" ]]; then
  if [[ ! -d "$LOCAL_QMD_SOURCE" ]]; then
    echo "LLM_WIKI_QMD_SOURCE does not exist: $LOCAL_QMD_SOURCE" >&2
    exit 1
  fi
  USE_LOCAL_QMD_SOURCE=1
fi

USE_LOCAL_GITVIZZ_SOURCE=0
if [[ -n "$LOCAL_GITVIZZ_SOURCE" ]]; then
  if [[ ! -d "$LOCAL_GITVIZZ_SOURCE" ]]; then
    echo "LLM_WIKI_GITVIZZ_SOURCE_HOST_PATH does not exist: $LOCAL_GITVIZZ_SOURCE" >&2
    exit 1
  fi
  USE_LOCAL_GITVIZZ_SOURCE=1
fi

if [[ "$ENABLE_GITVIZZ" == "1" && "$USE_LOCAL_GITVIZZ_SOURCE" != "1" && -z "$REMOTE_GITVIZZ_SOURCE" ]]; then
  echo "LLM_WIKI_ENABLE_GITVIZZ=1 requires LLM_WIKI_GITVIZZ_SOURCE_HOST_PATH or GCE_LLM_WIKI_GITVIZZ_SOURCE." >&2
  exit 1
fi

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
INSTANCE_SERVICE_ACCOUNT="${INSTANCE_SERVICE_ACCOUNT:-${PROJECT_NUMBER}-compute@developer.gserviceaccount.com}"

if [[ -n "$PUBLIC_MCP_SOURCE_RANGES" ]]; then
  OPEN_PUBLIC_MCP=1
fi

echo "Using project: $PROJECT_ID"
echo "Using image:   $IMAGE_URI"
echo "Using VM:      $INSTANCE_NAME ($ZONE)"

gcloud services enable \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  compute.googleapis.com \
  --project "$PROJECT_ID"

if ! gcloud artifacts repositories describe "$REPOSITORY_NAME" --location "$REGION" --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPOSITORY_NAME" \
    --project "$PROJECT_ID" \
    --repository-format docker \
    --location "$REGION" \
    --description "llm-wiki container images"
fi

TEMP_CLOUDBUILD=""
if [[ "$SKIP_BUILD" != "1" ]]; then
  TEMP_CLOUDBUILD="$(mktemp)"
  cat >"$TEMP_CLOUDBUILD" <<EOF
steps:
  - name: gcr.io/cloud-builders/docker
    args:
      - build
      - -f
      - docker/Dockerfile
      - -t
      - $IMAGE_URI
      - .
images:
  - $IMAGE_URI
EOF

  gcloud builds submit "$REPO_ROOT" \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --config "$TEMP_CLOUDBUILD"
fi

if [[ "$OPEN_PUBLIC_MCP" == "1" ]]; then
  if [[ -z "$PUBLIC_MCP_SOURCE_RANGES" ]]; then
    echo "OPEN_PUBLIC_MCP=1 requires PUBLIC_MCP_SOURCE_RANGES (or SOURCE_RANGES for backward compatibility)." >&2
    exit 1
  fi

  if ! gcloud compute firewall-rules describe "$PUBLIC_MCP_FIREWALL_RULE" --project "$PROJECT_ID" >/dev/null 2>&1; then
    gcloud compute firewall-rules create "$PUBLIC_MCP_FIREWALL_RULE" \
      --project "$PROJECT_ID" \
      --allow "tcp:${MCP_PORT}" \
      --target-tags "$INSTANCE_TAG" \
      --source-ranges "$PUBLIC_MCP_SOURCE_RANGES" \
      --description "Allow inbound llm-wiki MCP traffic"
  else
    gcloud compute firewall-rules update "$PUBLIC_MCP_FIREWALL_RULE" \
      --project "$PROJECT_ID" \
      --allow "tcp:${MCP_PORT}" \
      --target-tags "$INSTANCE_TAG" \
      --source-ranges "$PUBLIC_MCP_SOURCE_RANGES" \
      --description "Allow inbound llm-wiki MCP traffic"
  fi
else
  echo "Skipping public MCP firewall rule. Recommended hosted path is Cloudflare Tunnel plus a Worker or Access in front of the VM."
fi

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member "serviceAccount:${INSTANCE_SERVICE_ACCOUNT}" \
  --role "roles/artifactregistry.reader" \
  >/dev/null

if ! gcloud compute instances describe "$INSTANCE_NAME" --zone "$ZONE" --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud compute instances create "$INSTANCE_NAME" \
    --project "$PROJECT_ID" \
    --zone "$ZONE" \
    --machine-type "$MACHINE_TYPE" \
    --boot-disk-size "${BOOT_DISK_SIZE_GB}GB" \
    --image-family "$IMAGE_FAMILY" \
    --image-project "$IMAGE_PROJECT" \
    --service-account "$INSTANCE_SERVICE_ACCOUNT" \
    --scopes https://www.googleapis.com/auth/cloud-platform \
    --tags "$INSTANCE_TAG" \
    --metadata-from-file "startup-script=${SCRIPT_DIR}/startup.sh"
fi

echo "Waiting for SSH on $INSTANCE_NAME..."
until gcloud compute ssh "$INSTANCE_NAME" --project "$PROJECT_ID" --zone "$ZONE" --command "echo ready" >/dev/null 2>&1; do
  sleep 5
done

INSTANCE_IP="$(gcloud compute instances describe "$INSTANCE_NAME" --project "$PROJECT_ID" --zone "$ZONE" --format='value(networkInterfaces[0].accessConfigs[0].natIP)')"
if [[ -z "$QMD_MCP_URL" ]]; then
  if [[ "$OPEN_PUBLIC_MCP" == "1" ]]; then
    QMD_MCP_URL="http://${INSTANCE_IP}:${MCP_PORT}/mcp"
  else
    QMD_MCP_URL="http://127.0.0.1:${MCP_PORT}/mcp"
  fi
fi

TEMP_ENV="$(mktemp)"
QMD_STAGE_DIR=""
GITVIZZ_STAGE_DIR=""
cleanup() {
  rm -f "$TEMP_ENV"
  if [[ -n "$TEMP_CLOUDBUILD" ]]; then
    rm -f "$TEMP_CLOUDBUILD"
  fi
  if [[ -n "$QMD_STAGE_DIR" && -d "$QMD_STAGE_DIR" ]]; then
    rm -rf "$QMD_STAGE_DIR"
  fi
  if [[ -n "$GITVIZZ_STAGE_DIR" && -d "$GITVIZZ_STAGE_DIR" ]]; then
    rm -rf "$GITVIZZ_STAGE_DIR"
  fi
}
trap cleanup EXIT

cat >"$TEMP_ENV" <<EOF
LLM_WIKI_IMAGE=$IMAGE_URI
LLM_WIKI_VAULT_HOST_PATH=$REMOTE_VAULT_DIR
LLM_WIKI_HOME_HOST_PATH=$REMOTE_HOME_DIR
LLM_WIKI_QMD_SOURCE_HOST_PATH=$(if [[ "$USE_LOCAL_QMD_SOURCE" == "1" ]]; then printf '%s' "$REMOTE_QMD_SOURCE_DIR"; fi)
LLM_WIKI_MCP_PORT=$MCP_PORT
LLM_WIKI_TARGETS=$TARGETS
LLM_WIKI_FORCE_INSTALL=$FORCE_INSTALL
LLM_WIKI_SKIP_GITVIZZ=$SKIP_GITVIZZ
LLM_WIKI_ENABLE_GITVIZZ=$ENABLE_GITVIZZ
LLM_WIKI_GITVIZZ_SOURCE=$(if [[ "$USE_LOCAL_GITVIZZ_SOURCE" == "1" || -n "$REMOTE_GITVIZZ_SOURCE" ]]; then printf '%s' "$GITVIZZ_SOURCE"; fi)
LLM_WIKI_GITVIZZ_REPO_URL=$GITVIZZ_REPO_URL
LLM_WIKI_GITVIZZ_CHECKOUT_PATH=$GITVIZZ_CHECKOUT_PATH
LLM_WIKI_GITVIZZ_REPO_PATH=$(if [[ "$USE_LOCAL_GITVIZZ_SOURCE" == "1" || -n "$REMOTE_GITVIZZ_SOURCE" ]]; then printf '%s' "$GITVIZZ_SOURCE"; else printf '%s' "$GITVIZZ_REPO_PATH"; fi)
LLM_WIKI_GITVIZZ_FRONTEND_URL=$GITVIZZ_FRONTEND_URL
LLM_WIKI_GITVIZZ_BACKEND_URL=$GITVIZZ_BACKEND_URL
LLM_WIKI_GITVIZZ_WAIT_TIMEOUT=$GITVIZZ_WAIT_TIMEOUT
LLM_WIKI_GITVIZZ_SOURCE_HOST_PATH=$(if [[ "$USE_LOCAL_GITVIZZ_SOURCE" == "1" ]]; then printf '%s' "$REMOTE_GITVIZZ_SOURCE_DIR"; else printf '%s' "$REMOTE_GITVIZZ_SOURCE"; fi)
LLM_WIKI_GITVIZZ_MONGO_URI=$GITVIZZ_MONGO_URI
LLM_WIKI_GITVIZZ_PHOENIX_ENDPOINT=$GITVIZZ_PHOENIX_ENDPOINT
LLM_WIKI_GITVIZZ_PHOENIX_PROJECT_NAME=$GITVIZZ_PHOENIX_PROJECT_NAME
LLM_WIKI_GITVIZZ_BIND_HOST=$GITVIZZ_BIND_HOST
LLM_WIKI_QMD_SOURCE=$(if [[ "$USE_LOCAL_QMD_SOURCE" == "1" ]]; then printf '%s' "/qmd-source"; else printf '%s' "$REMOTE_QMD_SOURCE"; fi)
LLM_WIKI_QMD_REPO_URL=$QMD_REPO_URL
LLM_WIKI_QMD_MCP_URL=$QMD_MCP_URL
LLM_WIKI_BRV_COMMAND=$BRV_COMMAND
LLM_WIKI_MCP_SERVER_CMD=$MCP_SERVER_CMD
LLM_WIKI_MCP_UPSTREAM_HOST=$MCP_UPSTREAM_HOST
LLM_WIKI_MCP_BIND_HOST=$MCP_BIND_HOST
LLM_WIKI_AGENT_API_TOKEN=$AGENT_API_TOKEN
BYTEROVER_API_KEY=$BYTEROVER_API_KEY
OPENAI_API_KEY=$OPENAI_API_KEY
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
GROQ_API_KEY=$GROQ_API_KEY
GEMINI_API_KEY=$GEMINI_API_KEY
GH_TOKEN=$GH_TOKEN
GITHUB_TOKEN=$GITHUB_TOKEN
EOF

SCP_ITEMS=(
  "$SCRIPT_DIR/compose.yaml"
  "$TEMP_ENV"
)

if [[ "$USE_LOCAL_QMD_SOURCE" == "1" ]]; then
  QMD_STAGE_DIR="$(mktemp -d)"
  python3 - "$LOCAL_QMD_SOURCE" "$QMD_STAGE_DIR/pk-qmd-source" <<'PY'
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
  SCP_ITEMS+=(
    "$SCRIPT_DIR/compose.local-qmd.yml"
    "$QMD_STAGE_DIR/pk-qmd-source"
  )
fi

if [[ "$USE_LOCAL_GITVIZZ_SOURCE" == "1" ]]; then
  GITVIZZ_STAGE_DIR="$(mktemp -d)"
  python3 - "$LOCAL_GITVIZZ_SOURCE" "$GITVIZZ_STAGE_DIR/gitvizz-source" <<'PY'
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
  SCP_ITEMS+=(
    "$GITVIZZ_STAGE_DIR/gitvizz-source"
  )
fi

gcloud compute scp \
  --project "$PROJECT_ID" \
  --zone "$ZONE" \
  --recurse \
  "${SCP_ITEMS[@]}" \
  "${INSTANCE_NAME}:~/"

IMAGE_HOST="${IMAGE_URI%%/*}"
ENV_BASENAME="$(basename "$TEMP_ENV")"
REMOTE_COMMAND="$(cat <<EOF
set -euo pipefail
for attempt in \$(seq 1 30); do
  if sudo docker version >/dev/null 2>&1; then
    break
  fi
  sleep 5
done

sudo mkdir -p "$REMOTE_DEPLOY_DIR" "$REMOTE_VAULT_DIR" "$REMOTE_HOME_DIR"
sudo mv ~/compose.yaml "$REMOTE_DEPLOY_DIR/compose.yaml"
sudo mv ~/"$ENV_BASENAME" "$REMOTE_DEPLOY_DIR/llm-wiki.env"

compose_args=(-f compose.yaml)
if [[ "$USE_LOCAL_QMD_SOURCE" == "1" ]]; then
  sudo rm -rf "$REMOTE_QMD_SOURCE_DIR"
  sudo mkdir -p "$(dirname "$REMOTE_QMD_SOURCE_DIR")"
  sudo mv ~/compose.local-qmd.yml "$REMOTE_DEPLOY_DIR/compose.local-qmd.yml"
  sudo mv ~/pk-qmd-source "$REMOTE_QMD_SOURCE_DIR"
  compose_args+=(-f compose.local-qmd.yml)
fi

if [[ "$USE_LOCAL_GITVIZZ_SOURCE" == "1" ]]; then
  sudo rm -rf "$REMOTE_GITVIZZ_SOURCE_DIR"
  sudo mkdir -p "$(dirname "$REMOTE_GITVIZZ_SOURCE_DIR")"
  sudo mv ~/gitvizz-source "$REMOTE_GITVIZZ_SOURCE_DIR"
fi

if [[ "$ENABLE_GITVIZZ" == "1" ]]; then
  compose_args+=(--profile gitvizz)
fi

if [[ "$IMAGE_HOST" == *.pkg.dev ]]; then
  token=\$(curl -fsSL -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token" | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
  echo "\$token" | sudo docker login -u oauth2accesstoken --password-stdin "https://$IMAGE_HOST"
fi

cd "$REMOTE_DEPLOY_DIR"
sudo docker compose --env-file llm-wiki.env "\${compose_args[@]}" pull
sudo docker compose --env-file llm-wiki.env "\${compose_args[@]}" up -d
sudo docker compose --env-file llm-wiki.env "\${compose_args[@]}" ps
EOF
)"

gcloud compute ssh "$INSTANCE_NAME" \
  --project "$PROJECT_ID" \
  --zone "$ZONE" \
  --command "$REMOTE_COMMAND"

echo
echo "Deployment complete."
echo "VM:      $INSTANCE_NAME"
echo "Zone:    $ZONE"
echo "Image:   $IMAGE_URI"
echo "VM IP:   $INSTANCE_IP"
if [[ "$OPEN_PUBLIC_MCP" == "1" ]]; then
  echo "Direct MCP URL:  http://${INSTANCE_IP}:${MCP_PORT}/mcp"
else
  echo "Direct MCP URL:  not opened by this deploy script"
fi
echo "Config MCP URL:  $QMD_MCP_URL"
