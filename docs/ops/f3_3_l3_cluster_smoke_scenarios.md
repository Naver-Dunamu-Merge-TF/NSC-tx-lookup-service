# F3-3 L3 In-Cluster Smoke Scenarios (AKS)

## 1) Scope and Preconditions

- Cluster: `nsc-aks-dev`
- Namespace: `txlookup`
- Target service: admin API (`/admin/*`)
- Consumer and API pods must be `Ready`

Common pre-check command set:

```bash
az aks show -g 2dt-final-team4 -n nsc-aks-dev --query "{name:name, provisioningState:provisioningState}" -o json
kubectl get ns txlookup
kubectl -n txlookup get pods
```

## 2) Scenario Matrix

### L3-SMOKE-01: `/admin/tx/{tx_id}` returns `200`

- Prerequisites:
  - test `tx_id` already synced into backoffice DB
- Input/Event setup:
  - publish or select a known ledger event with concrete `tx_id`
- Execution command(s):

```bash
kubectl -n txlookup exec deploy/tx-lookup-api -- \
  curl -sS -o /tmp/l3_smoke_01.json -w "%{http_code}" \
  "http://127.0.0.1:8000/admin/tx/${TX_ID}"
```

- Expected API/metric result:
  - HTTP status `200`
  - response body contains same `tx_id`
- Pass/Fail criteria:
  - Pass when both status and `tx_id` match expected value

### L3-SMOKE-02: `/admin/tx/{tx_id}` returns `404` when missing

- Prerequisites:
  - synthetic missing id (`TX_ID_MISSING`) not present in backoffice DB
- Input/Event setup:
  - prepare random UUID and verify absence in DB snapshot
- Execution command(s):

```bash
kubectl -n txlookup exec deploy/tx-lookup-api -- \
  curl -sS -o /tmp/l3_smoke_02.json -w "%{http_code}" \
  "http://127.0.0.1:8000/admin/tx/${TX_ID_MISSING}"
```

- Expected API/metric result:
  - HTTP status `404`
  - response includes not-found semantics
- Pass/Fail criteria:
  - Pass when status code is `404` and response is consistent with not-found contract

### L3-SMOKE-03: pairing incomplete path with expected `pairing_status`

- Prerequisites:
  - related payment/order exists with only one side of ledger pair ingested
- Input/Event setup:
  - ingest single-side event (PAYMENT or RECEIVE only) for one `related_id`
- Execution command(s):

```bash
kubectl -n txlookup exec deploy/tx-lookup-api -- \
  curl -sS "http://127.0.0.1:8000/admin/tx/${TX_ID_INCOMPLETE}" \
  | tee /tmp/l3_smoke_03.json
```

- Expected API/metric result:
  - response `pairing_status` is `INCOMPLETE`
- Pass/Fail criteria:
  - Pass when pairing state is exactly `INCOMPLETE` and no contradictory pair payload exists

### L3-SMOKE-04: status-change freshness verification path

- Prerequisites:
  - payment order with mutable status exists
- Input/Event setup:
  - publish status-change event (`PENDING -> COMPLETED`) with fresh `updated_at`
- Execution command(s):

```bash
kubectl -n txlookup exec deploy/tx-lookup-api -- \
  curl -sS "http://127.0.0.1:8000/admin/payment-orders/${ORDER_ID}" \
  | tee /tmp/l3_smoke_04.json
```

- Expected API/metric result:
  - status-change reflected in API payload
  - freshness metric remains within SLO target (`consumer_freshness_seconds` p95 < 5s)
- Pass/Fail criteria:
  - Pass when updated status is visible and freshness evidence is within threshold

## 3) Evidence Output

Store each scenario output under:

- `.agents/logs/verification/<timestamp>_f3_3_l3_pass/10_l3_smoke_01.log`
- `.agents/logs/verification/<timestamp>_f3_3_l3_pass/11_l3_smoke_02.log`
- `.agents/logs/verification/<timestamp>_f3_3_l3_pass/12_l3_smoke_03.log`
- `.agents/logs/verification/<timestamp>_f3_3_l3_pass/13_l3_smoke_04.log`
