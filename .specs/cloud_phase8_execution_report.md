# Phase 8 Cloud-Test Execution Report

Last updated: 2026-02-06

## 1. Scope

Environment:
- Subscription: `27db5ec6-d206-4028-b5e1-6004dca5eeef`
- Resource group: `2dt-final-team4`
- Region: `koreacentral`

Goal:
- Complete `.roadmap/implementation_roadmap.md` Phase 8 (Cloud-Test) items end-to-end.

## 2. Provisioned resources

- Log Analytics: `team4-txlookup-law-2dt026-test`
- Application Insights: `team4-txlookup-ai-2dt026-test`
- Event Hubs namespace: `team4-txlookup-2dt026-test`
- Event hubs: `ledger.entry.upserted`, `payment.order.upserted`
- Consumer group: `bo-sync-test-2dt026-v1` (both hubs)
- PostgreSQL Flexible Server: `team4-txlookup-pg-2dt026-test` (public access)
- ACR: `team4txlookup2dt026test`
- Container Apps env: `team4-tx-caenv-2dt026-t`
- Container App(API): `team4-tx-api-2dt026-t`
- Container App(Consumer): `team4-tx-con-2dt026-t`

## 3. Deployment profile

- Messaging: Event Hubs Kafka endpoint
- Secrets: SAS/env injection (phase8 test profile)
- Consumer scaling: `min=1`, `max=1`
- API ingress: public HTTPS
- DB connection: `sslmode=require`

## 4. Validation results

Cloud smoke scenarios passed:
- `happy` (publish -> consume -> upsert -> API 200)
- `duplicate` (idempotent reprocess kept stable API result)
- `out_of_order` (newer version remained authoritative)
- `error` (invalid payload path produced consumer DLQ error log)
- missing tx check (API 404)

Destroy/Recreate validation:
- Resource-group lock blocked direct delete (`ScopeLocked`).
- Fallback executed: consumer scale cycle (`min 1 -> 0 -> 1`) and pipeline health revalidated.

## 5. Artifacts

Added execution automation:
- `scripts/cloud/phase8/provision_resources.sh`
- `scripts/cloud/phase8/build_push_images.sh`
- `scripts/cloud/phase8/run_db_migrations.sh`
- `scripts/cloud/phase8/deploy_apps.sh`
- `scripts/cloud/phase8/run_smoke.sh`
- `scripts/cloud/phase8/destroy_recreate_check.sh`
- `scripts/cloud/phase8/run_all.sh`
- `scripts/cloud/phase8/check_admin_tx.py`
- `scripts/publish_synthetic_events.py`

Container build assets:
- `docker/api.Dockerfile`
- `docker/consumer.Dockerfile`

## 6. Notes

- Container Apps names were shortened from the original naming proposal to meet Azure length constraints.
- RG lock behavior is retained; Phase 9 secure environment should assume separate, lock-aware deployment policy.
