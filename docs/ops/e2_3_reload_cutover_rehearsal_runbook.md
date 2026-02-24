# E2-3 Reload/Cutover Rehearsal Runbook (dev)

## 1) Scope

- Stage: `E2-3` (Cloud-Secure reload and cutover rehearsal)
- Environment: `dev`
- Goal: freeze and rehearse `alembic upgrade head -> backfill -> consumer sync` with cutover decision evidence
- Data source policy: synthetic-first (`scripts/publish_synthetic_events.py`)
- Private AKS execution path: jumpbox required (local direct `kubectl` path is non-default for private DNS environments)
- Out of scope:
  - Event Hubs resource/auth policy changes (external ownership)
  - runtime code changes in `src/`

## 2) Fixed Inputs

Set these variables first:

```bash
RUN_ID=e2-3-$(date -u +%Y%m%d%H%M%S)
EVIDENCE_DIR=.agents/logs/verification/$(date -u +%Y%m%d_%H%M%S)_e2_3_reload_cutover_rehearsal
mkdir -p "$EVIDENCE_DIR"

AKS_RESOURCE_GROUP=2dt-final-team4
AKS_CLUSTER=nsc-aks-dev
AKS_NAMESPACE=txlookup
API_SERVICE=tx-lookup-api
JUMPBOX_VM=jump-aks-20260224-2dt026
```

## 2.1) Jumpbox command wrapper (mandatory for private AKS)

Use this wrapper to execute all AKS commands through jumpbox:

```bash
SCRIPT=$(cat <<'EOF'
set -eu
sudo -u azureuser -H bash -lc 'az aks get-credentials -g 2dt-final-team4 -n nsc-aks-dev --overwrite-existing >/dev/null'
sudo -u azureuser -H bash -lc 'kubelogin convert-kubeconfig -l azurecli >/dev/null'
sudo -u azureuser -H bash -lc '<command>'
EOF
)
az vm run-command invoke \
  -g 2dt-final-team4 \
  -n "$JUMPBOX_VM" \
  --command-id RunShellScript \
  --scripts "$SCRIPT"
```

## 3) Preconditions

Readiness checks (`jumpbox` path):

```bash
az login
az aks show -g "$AKS_RESOURCE_GROUP" -n "$AKS_CLUSTER" --query provisioningState -o tsv

SCRIPT=$(cat <<'EOF'
set -eu
sudo -u azureuser -H bash -lc 'az aks get-credentials -g 2dt-final-team4 -n nsc-aks-dev --overwrite-existing >/dev/null'
sudo -u azureuser -H bash -lc 'kubelogin convert-kubeconfig -l azurecli >/dev/null'
sudo -u azureuser -H bash -lc 'kubectl get ns txlookup'
sudo -u azureuser -H bash -lc 'kubectl -n txlookup get deploy tx-lookup-api txlookup-consumer'
sudo -u azureuser -H bash -lc 'kubectl -n txlookup get pods'
EOF
)
az vm run-command invoke -g "$AKS_RESOURCE_GROUP" -n "$JUMPBOX_VM" --command-id RunShellScript --scripts "$SCRIPT"
```

Precondition acceptance:

- AKS `provisioningState=Succeeded`
- namespace `txlookup` is visible
- API/consumer deployments exist and pods are not in crashloop states

If precondition fails, classify run as `ENVIRONMENT_BLOCKED` and stop.

## 4) `T_cutover` Policy (UTC + Buffer Window)

`T_cutover` must be UTC ISO8601 and used as the single cut line for range split.
Buffer window is fixed to `+/-5 minutes` around `T_cutover` for operator guard checks.

```bash
T_cutover=$(date -u +%Y-%m-%dT%H:%M:%SZ)
BACKFILL_SINCE=$(date -u -d "$T_cutover -24 hours" +%Y-%m-%dT%H:%M:%SZ)
BACKFILL_UNTIL=$(date -u -d "$T_cutover -1 seconds" +%Y-%m-%dT%H:%M:%SZ)
SYNC_SINCE="$T_cutover"
```

Range contract:

- backfill range: `T_cutover-24h` to `T_cutover-1s`
- consumer sync range: `T_cutover` and later

## 5) Rehearsal Sequence

### 5.1 Generate synthetic JSONL for backfill

```bash
export RUN_ID T_cutover
.venv/bin/python - <<'PY'
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

run_id = os.environ["RUN_ID"]
t_cutover = datetime.fromisoformat(os.environ["T_cutover"].replace("Z", "+00:00"))
ts = (t_cutover - timedelta(hours=1)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
order_id = f"po-bf-{run_id}"
payment_tx = f"tx-bf-pay-{run_id}"
receive_tx = f"tx-bf-rec-{run_id}"

ledger_path = Path(f"/tmp/e2_3_ledger_{run_id}.jsonl")
payment_path = Path(f"/tmp/e2_3_payment_{run_id}.jsonl")

ledger_rows = [
    {
        "tx_id": payment_tx,
        "wallet_id": "wallet-bf-payer",
        "entry_type": "PAYMENT",
        "amount": "100.00",
        "amount_signed": "-100.00",
        "related_id": order_id,
        "related_type": "PAYMENT_ORDER",
        "event_time": ts,
        "created_at": ts,
        "updated_at": ts,
        "version": 1,
    },
    {
        "tx_id": receive_tx,
        "wallet_id": "wallet-bf-payee",
        "entry_type": "RECEIVE",
        "amount": "100.00",
        "amount_signed": "100.00",
        "related_id": order_id,
        "related_type": "PAYMENT_ORDER",
        "event_time": ts,
        "created_at": ts,
        "updated_at": ts,
        "version": 1,
    },
]

payment_rows = [
    {
        "order_id": order_id,
        "user_id": "user-bf",
        "merchant_name": "MERCHANT-BF",
        "amount": "100.00",
        "status": "SETTLED",
        "created_at": ts,
        "updated_at": ts,
        "version": 1,
    }
]

ledger_path.write_text(
    "\n".join(json.dumps(row, ensure_ascii=True) for row in ledger_rows) + "\n",
    encoding="utf-8",
)
payment_path.write_text(
    "\n".join(json.dumps(row, ensure_ascii=True) for row in payment_rows) + "\n",
    encoding="utf-8",
)
print(json.dumps({"ledger_file": str(ledger_path), "payment_file": str(payment_path), "order_id": order_id, "payment_tx_id": payment_tx}, ensure_ascii=True))
PY
```

### 5.2 Migration gate (`alembic upgrade head`)

```bash
SCRIPT=$(cat <<'EOF'
set -eu
sudo -u azureuser -H bash -lc 'az aks get-credentials -g 2dt-final-team4 -n nsc-aks-dev --overwrite-existing >/dev/null'
sudo -u azureuser -H bash -lc 'kubelogin convert-kubeconfig -l azurecli >/dev/null'
sudo -u azureuser -H bash -lc 'kubectl -n txlookup exec deploy/tx-lookup-api -- alembic upgrade head'
EOF
)
az vm run-command invoke -g "$AKS_RESOURCE_GROUP" -n "$JUMPBOX_VM" --command-id RunShellScript --scripts "$SCRIPT"
```

If failure: `MIGRATION_FAILED`.

### 5.3 Backfill gate

```bash
SCRIPT=$(cat <<EOF
set -eu
sudo -u azureuser -H bash -lc 'az aks get-credentials -g 2dt-final-team4 -n nsc-aks-dev --overwrite-existing >/dev/null'
sudo -u azureuser -H bash -lc 'kubelogin convert-kubeconfig -l azurecli >/dev/null'
sudo -u azureuser -H bash -lc "kubectl -n txlookup exec deploy/tx-lookup-api -- sh -lc 'python -m src.consumer.main backfill --ledger-file /tmp/e2_3_ledger_${RUN_ID}.jsonl --payment-order-file /tmp/e2_3_payment_${RUN_ID}.jsonl --since ${BACKFILL_SINCE} --until ${BACKFILL_UNTIL}'"
EOF
)
az vm run-command invoke -g "$AKS_RESOURCE_GROUP" -n "$JUMPBOX_VM" --command-id RunShellScript --scripts "$SCRIPT"
```

If failure: `BACKFILL_FAILED`.

### 5.4 Consumer sync gate (synthetic happy)

```bash
SCRIPT=$(cat <<EOF
set -eu
sudo -u azureuser -H bash -lc 'az aks get-credentials -g 2dt-final-team4 -n nsc-aks-dev --overwrite-existing >/dev/null'
sudo -u azureuser -H bash -lc 'kubelogin convert-kubeconfig -l azurecli >/dev/null'
sudo -u azureuser -H bash -lc "kubectl -n txlookup exec deploy/txlookup-consumer -- sh -lc 'python scripts/publish_synthetic_events.py --scenario happy --run-id ${RUN_ID}'"
sudo -u azureuser -H bash -lc "kubectl -n txlookup exec deploy/txlookup-consumer -- sh -lc 'python -m src.consumer.main consume --max-messages 3 --max-idle-seconds 20'"
EOF
)
az vm run-command invoke -g "$AKS_RESOURCE_GROUP" -n "$JUMPBOX_VM" --command-id RunShellScript --scripts "$SCRIPT"
```

If failure: `SYNC_FAILED`.

### 5.5 API smoke gate (`GET /admin/tx/{tx_id}` with 200 and 404)

Run from jumpbox using in-cluster API endpoint (`127.0.0.1:8000` in API pod).
Use single-line `python -c` calls (not nested heredoc) to avoid quoting issues in `az vm run-command invoke`.

```bash
SCRIPT=$(cat <<EOF
set -eu
sudo -u azureuser -H bash -lc 'az aks get-credentials -g 2dt-final-team4 -n nsc-aks-dev --overwrite-existing >/dev/null'
sudo -u azureuser -H bash -lc 'kubelogin convert-kubeconfig -l azurecli >/dev/null'
sudo -u azureuser -H bash -lc "kubectl -n txlookup exec deploy/tx-lookup-api -- python -c 'import requests,hashlib,sys; tx_id=\"${SYNC_TX_ID}\"; url=\"http://127.0.0.1:8000/admin/tx/\"+tx_id; r=requests.get(url, timeout=10); body=r.text; print(\"HTTP_CODE=\"+str(r.status_code)); print(\"BODY_SHA256=\"+hashlib.sha256(body.encode(\"utf-8\")).hexdigest()); print(\"BODY_LEN=\"+str(len(body))); sys.exit(0 if r.status_code==200 else 1)'"
sudo -u azureuser -H bash -lc "kubectl -n txlookup exec deploy/tx-lookup-api -- python -c 'import requests,sys; tx_id=\"tx-missing-${RUN_ID}\"; url=\"http://127.0.0.1:8000/admin/tx/\"+tx_id; r=requests.get(url, timeout=10); print(\"HTTP_CODE=\"+str(r.status_code)); print(\"BODY_LEN=\"+str(len(r.text))); sys.exit(0 if r.status_code==404 else 1)'"
EOF
)
az vm run-command invoke -g "$AKS_RESOURCE_GROUP" -n "$JUMPBOX_VM" --command-id RunShellScript --scripts "$SCRIPT"
```

Acceptance:

- first call returns `200`
- second call returns `404`

If failure: `SMOKE_FAILED`.

### 5.6 Idempotency gate (`duplicate` replay)

`GET /admin/tx/{tx_id}` 응답에는 시간 의존 필드(`data_lag_sec`)가 포함되므로 full payload hash를 그대로 비교하면 false negative가 발생할 수 있다.
또한 `scripts/publish_synthetic_events.py --scenario duplicate --run-id ...`는 재호출 시점의 `event_time`을 다시 생성하므로 `event_time`도 비교 대상에서 제외한다.

따라서 idempotency 비교는 **canonical payload hash** 기준으로 수행한다.

- canonical payload: response JSON에서 `event_time`, `data_lag_sec` 제거 후 정렬 직렬화(`sort_keys=True`)한 JSON

```bash
SCRIPT=$(cat <<EOF
set -eu
sudo -u azureuser -H bash -lc 'az aks get-credentials -g 2dt-final-team4 -n nsc-aks-dev --overwrite-existing >/dev/null'
sudo -u azureuser -H bash -lc 'kubelogin convert-kubeconfig -l azurecli >/dev/null'
sudo -u azureuser -H bash -lc "kubectl -n txlookup exec deploy/tx-lookup-api -- python -c 'import requests,hashlib,json; tx_id=\"${SYNC_TX_ID}\"; u=\"http://127.0.0.1:8000/admin/tx/\"+tx_id; r=requests.get(u, timeout=10); d=r.json(); s=dict(d); s.pop(\"event_time\", None); s.pop(\"data_lag_sec\", None); print(\"BEFORE_HTTP=\"+str(r.status_code)); print(\"BEFORE_CANON_HASH=\"+hashlib.sha256(json.dumps(s, sort_keys=True, separators=(\",\",\":\")).encode()).hexdigest())'"
sudo -u azureuser -H bash -lc "kubectl -n txlookup exec deploy/txlookup-consumer -- sh -lc 'python scripts/publish_synthetic_events.py --scenario duplicate --run-id ${RUN_ID}'"
sudo -u azureuser -H bash -lc "kubectl -n txlookup exec deploy/txlookup-consumer -- sh -lc 'python -m src.consumer.main consume --max-messages 6 --max-idle-seconds 20'"
sudo -u azureuser -H bash -lc "kubectl -n txlookup exec deploy/tx-lookup-api -- python -c 'import requests,hashlib,json; tx_id=\"${SYNC_TX_ID}\"; u=\"http://127.0.0.1:8000/admin/tx/\"+tx_id; r=requests.get(u, timeout=10); d=r.json(); s=dict(d); s.pop(\"event_time\", None); s.pop(\"data_lag_sec\", None); print(\"AFTER_HTTP=\"+str(r.status_code)); print(\"AFTER_CANON_HASH=\"+hashlib.sha256(json.dumps(s, sort_keys=True, separators=(\",\",\":\")).encode()).hexdigest())'"
EOF
)
az vm run-command invoke -g "$AKS_RESOURCE_GROUP" -n "$JUMPBOX_VM" --command-id RunShellScript --scripts "$SCRIPT"
```

Acceptance:

- `duplicate` 처리 전후 `BEFORE_HTTP=200`, `AFTER_HTTP=200`
- `BEFORE_CANON_HASH` == `AFTER_CANON_HASH`

If failure: `IDEMPOTENCY_FAILED`.

## 6) Decision and Rollback

Use the fixed matrix:

- `docs/ops/e2_3_cutover_rollback_decision_matrix.md`

Decision contract:

- `GO`: migration + backfill + sync + 200/404 + idempotency all pass
- `NO_GO`: any gate failed

`NO_GO` rollback contract:

- do not perform cutover promotion
- record failure classification, owner, retry_at_utc, unblock_criteria
- next attempt must set a new `T_cutover` and rerun full rehearsal

## 7) Evidence Storage Contract

Store all outputs under:

- `.agents/logs/verification/<timestamp>_e2_3_reload_cutover_rehearsal/`

Required filenames:

- `01_precheck.log`
- `02_alembic_upgrade.log`
- `03_backfill.log`
- `04_sync_happy.log`
- `05_smoke_200.log`
- `06_smoke_404.log`
- `07_idempotency_duplicate.log`
- `08_cutover_decision.log`
- `09_rollback_or_no_rollback.log`
- `99_summary.md`

Each evidence file must include:

- `command`
- `exit_code`
- `UTC timestamp`
- `owner`
- `result`
