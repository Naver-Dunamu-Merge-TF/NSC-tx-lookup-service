# F3-4 AKS Early Validation Runbook

## 1) Scope

- Validate AKS readiness: `provisioningState=Succeeded`
- Prepare and confirm `txlookup` namespace
- Run API/Consumer image pull and startup smoke
- Confirm DB/Event Hubs dependency connectivity
- Run in-cluster `GET /admin/tx/{tx_id}` smoke for `200` and `404`
- Capture consumer lag and `consumer_freshness_seconds` evidence

## 2) Baseline Checks

- AKS readiness gate: `provisioningState=Succeeded`
- Namespace gate: `txlookup` exists and ready
- Fixed precheck order: `az login` -> AKS state -> kubeconfig -> namespace

### 2.1) Authentication and AKS state precheck

```bash
az login
az aks show -g 2dt-final-team4 -n nsc-aks-dev --query provisioningState -o tsv
```

Expected state: `provisioningState=Succeeded`.

Blocked handling:

- If AKS state is not `Succeeded`, stop F3-4 execution.
- Classify as `ENVIRONMENT_BLOCKED` and store evidence.

### 2.2) Kubeconfig + namespace preparation

```bash
az aks get-credentials -g 2dt-final-team4 -n nsc-aks-dev --overwrite-existing
kubectl get ns txlookup || kubectl create ns txlookup
kubectl get ns txlookup
```

Create-if-missing branch:

- If `kubectl get ns txlookup` fails, run `kubectl create ns txlookup`.
- Re-run `kubectl get ns txlookup` and continue only when namespace is visible.

### 2.3) Readiness evidence naming

Store logs under `.agents/logs/verification/<timestamp>_f3_4_readiness/`:

- `01_aks_provisioning_state.log`
- `02_kubeconfig_get_credentials.log`
- `03_txlookup_namespace.log`

## 3) API/Consumer Startup Smoke

Set startup inputs:

```bash
API_DEPLOYMENT=txlookup-api
CONSUMER_DEPLOYMENT=txlookup-consumer
API_IMAGE=<acr>/<repo>/txlookup-api:<tag>
CONSUMER_IMAGE=<acr>/<repo>/txlookup-consumer:<tag>
```

Validate deployment names before rollout:

```bash
kubectl -n txlookup get deploy
```

Apply image update and wait for rollout:

```bash
kubectl -n txlookup set image deployment/${API_DEPLOYMENT} ${API_DEPLOYMENT}=${API_IMAGE}
kubectl -n txlookup set image deployment/${CONSUMER_DEPLOYMENT} ${CONSUMER_DEPLOYMENT}=${CONSUMER_IMAGE}
kubectl -n txlookup rollout status deployment/${API_DEPLOYMENT}
kubectl -n txlookup rollout status deployment/${CONSUMER_DEPLOYMENT}
```

Dependency checks after rollout:

- DB connection: inspect API/Consumer logs for successful DB connection messages
- Event Hubs connection: inspect Consumer logs for successful Event Hubs connection and active consume loop

Rollback policy:

- If image pull or rollout fails, rollback to previous image tag and re-run rollout status checks before continuing.

## 4) API Smoke

Run in-cluster API smoke:

```bash
API_BASE_URL=http://txlookup-api.txlookup.svc.cluster.local:8000
KNOWN_TX_ID=<existing_tx_id>
MISSING_TX_ID=missing-tx-id

curl -sS -o /tmp/f3_4_tx_200.json -w '%{http_code}\n' \
  "${API_BASE_URL}/admin/tx/${KNOWN_TX_ID}"
curl -sS -o /tmp/f3_4_tx_404.json -w '%{http_code}\n' \
  "${API_BASE_URL}/admin/tx/${MISSING_TX_ID}"
```

Acceptance:

- `GET /admin/tx/{tx_id}` returns 200 for known `tx_id`
- `GET /admin/tx/{tx_id}` returns 404 for missing `tx_id`

## 5) Metrics Evidence

Lag/freshness evidence query path priority:

- primary: Azure Monitor `AppMetrics` evidence logs using `docs/ops/f3_2_slo_alerts_runbook.md` KQL baseline
- fallback: cluster metrics evidence only when Azure Monitor query path is unavailable; classify `failure_classification=MONITORING_ACCESS_BLOCKED` and capture unblock owner/retry

Required metrics:

- consumer lag
- `consumer_freshness_seconds`

Failure classes:

- `ENVIRONMENT_BLOCKED`
- `STARTUP_FAILED`
- `SMOKE_FAILED`
- `METRIC_FAILED`
- `MONITORING_ACCESS_BLOCKED`

Store logs under `.agents/logs/verification/`
