# E2-3 Cutover Decision Matrix (GO/NO_GO)

## 1) Scope

This matrix defines the fixed cutover decision for E2-3 rehearsal.
Decision values are only `GO` or `NO_GO`.

## 2) Gate Matrix

| Gate | Pass Criteria | Failure Classification | `NO_GO` Action |
| --- | --- | --- | --- |
| Migration | `.venv/bin/alembic upgrade head` succeeds | `MIGRATION_FAILED` | stop run, keep current deployment |
| Backfill | synthetic JSONL backfill succeeds in range `< T_cutover` | `BACKFILL_FAILED` | stop run, investigate payload/range |
| Sync | synthetic happy publish + consume succeeds for `>= T_cutover` | `SYNC_FAILED` | stop run, inspect consumer/event path |
| Smoke | `GET /admin/tx/{tx_id}` returns `200` and missing id returns `404` | `SMOKE_FAILED` | stop run, inspect API/read path |
| Idempotency | duplicate replay keeps canonical payload hash unchanged (`event_time`, `data_lag_sec` excluded) | `IDEMPOTENCY_FAILED` | stop run, inspect upsert/idempotency path |

## 3) Decision Rule

- Idempotency gate hash baseline:
  - Build hash from response JSON after removing `event_time`, `data_lag_sec`.
  - Compare normalized JSON (`sort_keys=True`) hash before/after duplicate replay.

- `GO`:
  - all gates pass
  - no unresolved blocker in evidence summary
- `NO_GO`:
  - any gate fails
  - missing evidence file is treated as failure

## 4) Rollback and Retry Contract (`NO_GO`)

When decision is `NO_GO`, apply all rules:

1. Cutover promotion is not executed.
2. Record one primary failure classification:
   - `ENVIRONMENT_BLOCKED`
   - `MIGRATION_FAILED`
   - `BACKFILL_FAILED`
   - `SYNC_FAILED`
   - `SMOKE_FAILED`
   - `IDEMPOTENCY_FAILED`
3. Record `owner`, `retry_at_utc`, `unblock_criteria`.
4. Next run must use a new `T_cutover` (UTC) and rerun full sequence.

## 5) Evidence Summary Template

```text
decision=<GO|NO_GO>
failure_classification=<ENVIRONMENT_BLOCKED|MIGRATION_FAILED|BACKFILL_FAILED|SYNC_FAILED|SMOKE_FAILED|IDEMPOTENCY_FAILED|NONE>
t_cutover_utc=<YYYY-MM-DDTHH:MM:SSZ>
owner=<owner>
retry_at_utc=<YYYY-MM-DDTHH:MM:SSZ or N/A>
unblock_criteria=<explicit criteria or N/A>
notes=<short summary>
```
