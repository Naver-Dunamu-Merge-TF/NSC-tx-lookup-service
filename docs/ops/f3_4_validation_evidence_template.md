# F3-4 Validation Evidence Template

## 1) Run Metadata

- Run ID: `<timestamp>_f3_4_validation`
- UTC timestamp: `<YYYY-MM-DDTHH:MM:SSZ>`
- Owner: `<name>`

## 2) Required Evidence

- AKS state includes `provisioningState=Succeeded`
- `txlookup` namespace readiness proof
- API/Consumer image pull and startup logs
- DB/Event Hubs connectivity logs
- `GET /admin/tx/{tx_id}` `200` and `404` smoke outputs
- consumer lag evidence
- `consumer_freshness_seconds` evidence

## 3) Evidence Path

- Save under `.agents/logs/verification/`

## 4) API Smoke Contract

- `GET /admin/tx/{tx_id}` returns 200 for known `tx_id`
- `GET /admin/tx/{tx_id}` returns 404 for missing `tx_id`

## 5) Failure and Retry Contract

- `failure_classification=<ENVIRONMENT_BLOCKED|STARTUP_FAILED|SMOKE_FAILED|METRIC_FAILED|MONITORING_ACCESS_BLOCKED>`
- `retry_at_utc=<YYYY-MM-DDTHH:MM:SSZ>`
- `unblock_criteria=<explicit criteria>`
- `owner=<responsible owner>`
