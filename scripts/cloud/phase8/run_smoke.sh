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

wait_for_tx() {
  local tx_id="$1"
  local expected_paired="$2"
  local expected_amount="$3"
  local expected_pairing_status="$4"
  local attempts="${5:-45}"

  local i
  for ((i = 1; i <= attempts; i++)); do
    if python "$ROOT_DIR/scripts/cloud/phase8/check_admin_tx.py" \
      --base-url "$API_BASE_URL" \
      --tx-id "$tx_id" \
      --expect-status 200 \
      --expect-paired "$expected_paired" \
      --expect-amount "$expected_amount" \
      --expect-pairing-status "$expected_pairing_status" \
      >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done

  python "$ROOT_DIR/scripts/cloud/phase8/check_admin_tx.py" \
    --base-url "$API_BASE_URL" \
    --tx-id "$tx_id" \
    --expect-status 200 \
    --expect-paired "$expected_paired" \
    --expect-amount "$expected_amount" \
    --expect-pairing-status "$expected_pairing_status"
}

RUN_ID_BASE="${RUN_ID_BASE:-phase8$(date +%Y%m%d%H%M%S)}"
echo "[phase8-smoke] api=$API_BASE_URL run_id_base=$RUN_ID_BASE"

# 1) happy path
HAPPY_ID="${RUN_ID_BASE}-happy"
python "$ROOT_DIR/scripts/publish_synthetic_events.py" --scenario happy --run-id "$HAPPY_ID" >/dev/null
wait_for_tx "tx-pay-${HAPPY_ID}" "tx-rec-${HAPPY_ID}" "100.00" "COMPLETE"
python "$ROOT_DIR/scripts/cloud/phase8/check_admin_tx.py" \
  --base-url "$API_BASE_URL" \
  --tx-id "tx-missing-${RUN_ID_BASE}" \
  --expect-status 404 \
  >/dev/null
echo "[phase8-smoke] happy + 404 check passed"

# 2) duplicate/idempotency
DUP_ID="${RUN_ID_BASE}-dup"
python "$ROOT_DIR/scripts/publish_synthetic_events.py" --scenario duplicate --run-id "$DUP_ID" >/dev/null
wait_for_tx "tx-pay-${DUP_ID}" "tx-rec-${DUP_ID}" "100.00" "COMPLETE"
before="$(python "$ROOT_DIR/scripts/cloud/phase8/check_admin_tx.py" \
  --base-url "$API_BASE_URL" \
  --tx-id "tx-pay-${DUP_ID}" \
  --expect-status 200 \
  --expect-paired "tx-rec-${DUP_ID}" \
  --expect-amount "100.00" \
  --expect-pairing-status COMPLETE)"
python "$ROOT_DIR/scripts/publish_synthetic_events.py" --scenario duplicate --run-id "$DUP_ID" >/dev/null
wait_for_tx "tx-pay-${DUP_ID}" "tx-rec-${DUP_ID}" "100.00" "COMPLETE"
after="$(python "$ROOT_DIR/scripts/cloud/phase8/check_admin_tx.py" \
  --base-url "$API_BASE_URL" \
  --tx-id "tx-pay-${DUP_ID}" \
  --expect-status 200 \
  --expect-paired "tx-rec-${DUP_ID}" \
  --expect-amount "100.00" \
  --expect-pairing-status COMPLETE)"
python - "$before" "$after" <<'PY'
import json
import sys
before = json.loads(sys.argv[1])
after = json.loads(sys.argv[2])
keys = ["tx_id", "paired_tx_id", "amount", "pairing_status", "related"]
for key in keys:
    if before.get(key) != after.get(key):
        raise SystemExit(f"idempotency mismatch at {key}: {before.get(key)} != {after.get(key)}")
PY
echo "[phase8-smoke] duplicate/idempotency check passed"

# 3) out-of-order protection
OOO_ID="${RUN_ID_BASE}-ooo"
python "$ROOT_DIR/scripts/publish_synthetic_events.py" --scenario out_of_order --run-id "$OOO_ID" >/dev/null
wait_for_tx "tx-pay-${OOO_ID}" "tx-rec-${OOO_ID}" "200.00" "COMPLETE"
echo "[phase8-smoke] out-of-order check passed"

# 4) error path / DLQ signal
ERR_ID="${RUN_ID_BASE}-err"
python "$ROOT_DIR/scripts/publish_synthetic_events.py" --scenario error --run-id "$ERR_ID" >/dev/null
sleep 8
logs_text="$(az containerapp logs show \
  --resource-group "$AZ_RESOURCE_GROUP" \
  --name "$CA_CONSUMER_NAME" \
  --tail 300 \
  --format text)"
if ! grep -q "Failed to process message; sent to DLQ" <<<"$logs_text"; then
  echo "$logs_text" | tail -n 80
  echo "[phase8-smoke] expected DLQ error log not found"
  exit 1
fi
echo "[phase8-smoke] error/DLQ check passed"

echo "[phase8-smoke] all checks passed"
