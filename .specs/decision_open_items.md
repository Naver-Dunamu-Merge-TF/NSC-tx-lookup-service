# Decision Open Items

Last updated: 2026-02-06

## Open items
| ID | Topic | Current assumption/implementation | Why decision needed | Next step |
| --- | --- | --- | --- | --- |
| DEC-001 | OIDC claim mapping (roles/actor id) | Defaults: `AUTH_ROLES_CLAIM=roles`, `AUTH_ACTOR_ID_CLAIMS=sub` | Entra app registration may emit roles in `roles` or `scp`; actor id may be `oid` or `sub` | Confirm actual claims from Entra token and update config/env docs |
| DEC-002 | DLQ storage backend (prod) | Local default uses JSONL file `./dlq/failed_events.jsonl` | File is not durable/observable for prod | Choose Kafka topic vs DB table vs object storage |
| DEC-003 | `status_group` mapping | API returns `status_group="UNKNOWN"` | Needs business mapping for `payment_orders.status` to groups | Define mapping table and update API response |
| DEC-004 | Pairing regression policy | `should_update_pair` blocks complete → incomplete updates | Reversals/refunds may require different policy | Decide if complete pairs can be overwritten by later events |
| DEC-005 | `related_type` expansion | Pairing only for `PAYMENT_ORDER`, others → `UNKNOWN` | Future domains may need pairing logic | Define supported related types and rules |
| DEC-006 | `amount_signed` source of truth | Uses event payload when present; no derivation if missing | Need consistency rule across upstream data | Decide whether to compute from `amount` + entry type when absent |
| DEC-007 | Slow query threshold | `DB_SLOW_QUERY_MS=200` for slow-query logging | Aligns DB slow query definition with SLOs | Confirm threshold per environment |
| DEC-008 | Consumer freshness timestamp | Uses `ledger.event_time` and `payment_order.updated_at` fallback to `created_at` | Defines end-to-end freshness metric basis | Confirm which timestamp best represents OLTP commit time |
| DEC-009 | Correlation ID header | Uses `X-Correlation-ID` for inbound/outbound propagation | Ensure compatibility with existing gateway conventions | Confirm standard header name |
| DEC-010 | Alert thresholds (API error rate, DLQ) | Prometheus alerts: API error rate >2% for 5m, DLQ activity >0 for 5m | Thresholds are org/ops-specific and may cause alert noise | Confirm desired thresholds and severities |

## Decided
| ID | Topic | Decision | Evidence |
| --- | --- | --- | --- |
| DEC-101 | OIDC provider | Microsoft Entra ID | `configs/README.md` (OIDC provider section) |
| DEC-102 | Audit log storage | Persist to `bo.admin_audit_logs` table | `src/db/models.py`, `migrations/20260205_0003_create_admin_audit_logs.py` |
| DEC-103 | Pairing store | Use Backoffice DB `bo.payment_ledger_pairs` | `migrations/20260205_0001_create_backoffice_schema.py` |
| DEC-104 | Event Hubs ownership model (Phase 8 test) | Use isolated Event Hubs namespace per owner; do not share team namespace for disposable test environments | `.roadmap/implementation_roadmap.md` (Phase 8 Cloud-Test item) |
| DEC-105 | Cloud test runtime | Use `Event Hubs (Kafka) + Azure Container Apps` for Phase 8 test stack; production target may remain AKS | `.roadmap/implementation_roadmap.md` (Phase 8 Cloud-Test item) |
| DEC-106 | Cloud test secret delivery | Use simplest test profile: SAS/env injection first; defer Key Vault+Managed Identity hardening to secure rebuild phase | `.roadmap/implementation_roadmap.md` (Phase 8 Cloud-Test item), `.specs/cloud_migration_rebuild_plan.md` |
| DEC-107 | Event Hubs baseline contract (Phase 8 test) | Use hubs `ledger.entry.upserted` and `payment.order.upserted`, partition=2 each, retention=3 days, consumer group naming `bo-sync-<env>-<owner>-v1` | `.specs/cloud_migration_rebuild_plan.md`, `.roadmap/implementation_roadmap.md` |
| DEC-108 | Cloud promotion model | Use two-stage promotion: Cloud-Test(disposable/public) -> Cloud-Secure(separate/secured), no in-place hardening | `.specs/cloud_migration_rebuild_plan.md`, `.roadmap/implementation_roadmap.md`, `.specs/backoffice_project_specs.md` |
| DEC-109 | Container Apps test naming | Keep `team4-txlookup-*` base pattern, but shorten Container Apps names to <=32 chars (`team4-tx-caenv-2dt026-t`, `team4-tx-api-2dt026-t`, `team4-tx-con-2dt026-t`) due Azure name limit | `.specs/cloud_test_resource_naming.md`, `scripts/cloud/phase8/provision_resources.sh` |
| DEC-110 | Destroy/Recreate test under RG lock | If delete is blocked by resource-group lock, use consumer scale cycle (`min 1 -> 0 -> 1`) as Phase 8 recreate fallback and verify pipeline resumes | `scripts/cloud/phase8/destroy_recreate_check.sh`, `.roadmap/implementation_roadmap.md` |
