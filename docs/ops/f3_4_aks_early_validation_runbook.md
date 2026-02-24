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
API_DEPLOYMENT=tx-lookup-api
API_CONTAINER=api
CONSUMER_DEPLOYMENT=txlookup-consumer
API_IMAGE=<acr>/<repo>/txlookup-api:<tag>
CONSUMER_IMAGE=<acr>/<repo>/txlookup-consumer:<tag>
```

Repository fallback policy:

- If `txlookup/consumer` repository/tag is missing in ACR, reuse `API_IMAGE` for consumer and force consumer command override (`python -m src.consumer.main consume`).
- Record the fallback reason in evidence and keep a follow-up item for image repository contract alignment.

Validate deployment names before rollout:

```bash
kubectl -n txlookup get deploy
```

Precheck ACR reachability from the same execution path (jumpbox):

```bash
az acr check-health -n nscacrdevw4mlu8 --yes
```

Blocked handling:

- If ACR login server is unreachable (for example, `Could not connect to the registry login server`), classify as `ENVIRONMENT_BLOCKED` and stop closeout.
- Record retry owner/date/unblock criteria before re-run.

Consumer env contract check:

- `txlookup-api-env` may contain API-only keys (`APP_ENV`, `AUTH_MODE`, `DATABASE_URL`) and miss Kafka settings.
- Before rollout, ensure consumer has Kafka/Event Hubs env keys:
  - `KAFKA_BROKERS`
  - `KAFKA_SECURITY_PROTOCOL`
  - `KAFKA_SASL_MECHANISM`
  - `KAFKA_SASL_USERNAME`
  - `KAFKA_SASL_PASSWORD`
  - `EVENT_PROFILE_ID`
- For metric evidence collection, ensure `APPLICATIONINSIGHTS_CONNECTION_STRING` is present for consumer runtime.
- If missing, inject a dedicated secret (for example `txlookup-consumer-kafka-env`) and set env from both secrets.

Apply image update and wait for rollout:

```bash
kubectl -n txlookup set image deployment/${API_DEPLOYMENT} ${API_CONTAINER}=${API_IMAGE}
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
# jumpbox path: use kubectl port-forward, then curl localhost
kubectl -n txlookup port-forward svc/tx-lookup-api 18000:8000

KNOWN_TX_ID=<existing_tx_id>
MISSING_TX_ID=missing-tx-id

curl -sS -o /tmp/f3_4_tx_200.json -w '%{http_code}\n' \
  "http://127.0.0.1:18000/admin/tx/${KNOWN_TX_ID}"
curl -sS -o /tmp/f3_4_tx_404.json -w '%{http_code}\n' \
  "http://127.0.0.1:18000/admin/tx/${MISSING_TX_ID}"
```

If you execute from inside a cluster pod, service DNS (`tx-lookup-api.txlookup.svc.cluster.local`) is allowed.

Acceptance:

- `GET /admin/tx/{tx_id}` returns 200 for known `tx_id`
- `GET /admin/tx/{tx_id}` returns 404 for missing `tx_id`

## 5) Metrics Evidence

Lag/freshness evidence query path priority:

- primary: Azure Monitor `AppMetrics` evidence logs using `docs/ops/f3_2_slo_alerts_runbook.md` KQL baseline
- fallback: cluster metrics evidence only when Azure Monitor query path is unavailable; classify `failure_classification=MONITORING_ACCESS_BLOCKED` and capture unblock owner/retry

Collection path precheck before AppMetrics pass/fail decision:

- Consumer pod env includes `APPLICATIONINSIGHTS_CONNECTION_STRING`.
- Consumer startup log includes `Azure Monitor OpenTelemetry configured`.
- For Firewall egress environments, ensure telemetry FQDN allowlist exists for Application subnet:
  - `dc.services.visualstudio.com`
  - `*.in.applicationinsights.azure.com`
  - `*.livediagnostics.monitor.azure.com`
- If AppMetrics query path is reachable but rows stay empty, inspect consumer exporter logs.
  - If logs show `UNEXPECTED_EOF_WHILE_READING` while posting to Application Insights ingestion endpoint, classify `failure_classification=ENVIRONMENT_BLOCKED` (AKS pod egress/TLS path), not `METRIC_FAILED`.
  - Record retry owner/date and unblock criteria (`pod SSL handshake to ingestion endpoint succeeds` + AppMetrics rows appear).

Required metrics:

- `consumer_kafka_lag`
- `consumer_freshness_seconds`

`consumer_kafka_lag` capture rule:

- Normal path: use broker watermark offsets to calculate lag.
- Fallback path: if watermark lookup returns `None` or raises, record lag as `0` for that poll cycle.
- Interpretation: sustained `0` values with known backlog must trigger broker/watermark capability diagnostics (do not treat as guaranteed empty backlog).

Failure classes:

- `ENVIRONMENT_BLOCKED`
- `STARTUP_FAILED`
- `SMOKE_FAILED`
- `METRIC_FAILED`
- `MONITORING_ACCESS_BLOCKED`

Store logs under `.agents/logs/verification/`
