# E2-3 Validation Evidence Template

## 1) Metadata

- `owner`:
- `result`: `PASS|FAIL|BLOCKED`
- `environment`: `dev`
- `t_cutover_utc`: `<YYYY-MM-DDTHH:MM:SSZ>`
- `evidence_dir`: `.agents/logs/verification/<timestamp>_e2_3_reload_cutover_rehearsal/`

## 2) Command Capture Format

For each evidence file, record:

- `command`
- `exit_code`
- `UTC timestamp`
- `owner`
- `result`

## 3) Required Evidence Files

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

## 4) Summary Template

```text
owner=<owner>
result=<PASS|FAIL|BLOCKED>
decision=<GO|NO_GO>
failure_classification=<ENVIRONMENT_BLOCKED|MIGRATION_FAILED|BACKFILL_FAILED|SYNC_FAILED|SMOKE_FAILED|IDEMPOTENCY_FAILED|NONE>
t_cutover_utc=<YYYY-MM-DDTHH:MM:SSZ>
started_at_utc=<YYYY-MM-DDTHH:MM:SSZ>
ended_at_utc=<YYYY-MM-DDTHH:MM:SSZ>
retry_at_utc=<YYYY-MM-DDTHH:MM:SSZ or N/A>
unblock_criteria=<explicit criteria or N/A>
notes=<short summary>
```
