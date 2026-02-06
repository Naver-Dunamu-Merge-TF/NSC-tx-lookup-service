#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="${PHASE8_ENV_FILE:-$ROOT_DIR/.env/phase8_cloud_test.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "missing env file: $ENV_FILE"
  echo "run scripts/cloud/phase8/provision_resources.sh first"
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

az account set --subscription "$AZ_SUBSCRIPTION_ID"

if [[ -z "${API_BASE_URL:-}" ]]; then
  API_FQDN="$(az containerapp show --resource-group "$AZ_RESOURCE_GROUP" --name "$CA_API_NAME" --query properties.configuration.ingress.fqdn -o tsv)"
  API_BASE_URL="https://${API_FQDN}"
fi

echo "[phase8-recreate] trying delete -> recreate for consumer app"
delete_output=""
if az containerapp show --resource-group "$AZ_RESOURCE_GROUP" --name "$CA_CONSUMER_NAME" >/dev/null 2>&1; then
  set +e
  delete_output="$(az containerapp delete \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --name "$CA_CONSUMER_NAME" \
    --yes 2>&1)"
  delete_rc=$?
  set -e

  if [[ $delete_rc -eq 0 ]]; then
    DEPLOY_API=0 DEPLOY_CONSUMER=1 PHASE8_ENV_FILE="$ENV_FILE" \
      "$ROOT_DIR/scripts/cloud/phase8/deploy_apps.sh" >/dev/null
  else
    if grep -q "ScopeLocked" <<<"$delete_output"; then
      echo "[phase8-recreate] resource group lock detected, using scale cycle fallback"
      az containerapp update \
        --resource-group "$AZ_RESOURCE_GROUP" \
        --name "$CA_CONSUMER_NAME" \
        --min-replicas 0 \
        --max-replicas 1 \
        >/dev/null
      sleep 8
      az containerapp update \
        --resource-group "$AZ_RESOURCE_GROUP" \
        --name "$CA_CONSUMER_NAME" \
        --min-replicas 1 \
        --max-replicas 1 \
        >/dev/null
    else
      echo "$delete_output"
      exit 1
    fi
  fi
else
  DEPLOY_API=0 DEPLOY_CONSUMER=1 PHASE8_ENV_FILE="$ENV_FILE" \
    "$ROOT_DIR/scripts/cloud/phase8/deploy_apps.sh" >/dev/null
fi

for _ in $(seq 1 30); do
  running="$(az containerapp show \
    --resource-group "$AZ_RESOURCE_GROUP" \
    --name "$CA_CONSUMER_NAME" \
    --query properties.runningStatus -o tsv 2>/dev/null || true)"
  if [[ "$running" == "Running" ]]; then
    break
  fi
  sleep 3
done

RUN_ID="${RUN_ID_BASE:-recreate$(date +%Y%m%d%H%M%S)}"
python "$ROOT_DIR/scripts/publish_synthetic_events.py" --scenario happy --run-id "$RUN_ID" >/dev/null

for _ in $(seq 1 45); do
  if python "$ROOT_DIR/scripts/cloud/phase8/check_admin_tx.py" \
    --base-url "$API_BASE_URL" \
    --tx-id "tx-pay-${RUN_ID}" \
    --expect-status 200 \
    --expect-paired "tx-rec-${RUN_ID}" \
    --expect-amount "100.00" \
    --expect-pairing-status COMPLETE \
    >/dev/null 2>&1; then
    echo "[phase8-recreate] destroy -> recreate check passed"
    exit 0
  fi
  sleep 2
done

python "$ROOT_DIR/scripts/cloud/phase8/check_admin_tx.py" \
  --base-url "$API_BASE_URL" \
  --tx-id "tx-pay-${RUN_ID}" \
  --expect-status 200 \
  --expect-paired "tx-rec-${RUN_ID}" \
  --expect-amount "100.00" \
  --expect-pairing-status COMPLETE
