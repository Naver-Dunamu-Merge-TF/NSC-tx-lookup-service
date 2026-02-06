#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="${PHASE8_ENV_FILE:-$ROOT_DIR/.env/phase8_cloud_test.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "missing env file: $ENV_FILE"
  echo "run scripts/cloud/phase8/provision_resources.sh first"
  exit 1
fi

source "$ENV_FILE"

az config set extension.use_dynamic_install=yes_without_prompt >/dev/null
az account set --subscription "$AZ_SUBSCRIPTION_ID"

IMAGE_TAG="${IMAGE_TAG_OVERRIDE:-phase8-$(date +%Y%m%d%H%M%S)}"
API_IMAGE="${ACR_LOGIN_SERVER}/txlookup-api:${IMAGE_TAG}"
CONSUMER_IMAGE="${ACR_LOGIN_SERVER}/txlookup-consumer:${IMAGE_TAG}"

echo "[phase8] building images in ACR: $ACR_NAME tag=$IMAGE_TAG"
az acr build \
  --registry "$ACR_NAME" \
  --file docker/api.Dockerfile \
  --image "txlookup-api:${IMAGE_TAG}" \
  "$ROOT_DIR" \
  >/dev/null

az acr build \
  --registry "$ACR_NAME" \
  --file docker/consumer.Dockerfile \
  --image "txlookup-consumer:${IMAGE_TAG}" \
  "$ROOT_DIR" \
  >/dev/null

{
  printf "IMAGE_TAG=%q\n" "$IMAGE_TAG"
  printf "API_IMAGE=%q\n" "$API_IMAGE"
  printf "CONSUMER_IMAGE=%q\n" "$CONSUMER_IMAGE"
} >>"$ENV_FILE"

echo "[phase8] image build complete"
echo "[phase8] API image: $API_IMAGE"
echo "[phase8] Consumer image: $CONSUMER_IMAGE"
