# E2-2 Validation Evidence Template

## 1) Metadata

- `owner`:
- `result`:
- `environment`: `dev`
- `evidence_dir`: `.agents/logs/verification/<timestamp>_e2_2_secret_rbac_gate/`

## 2) Command Capture Format

For each evidence step, record:

- `command`
- `exit_code`
- UTC timestamp
- `owner`
- `result`

## 3) Required Evidence Files

- `01_l0.log`
- `02_l1_docs.log`
- `03_l1_auth_path.log`
- `04_secret_transition_contract.log`
- `05_rbac_matrix_contract.log`
- `06_auth_observability_contract.log`
- `99_summary.md`

## 4) Summary Template

```text
owner=<owner>
result=<PASS|FAIL|BLOCKED>
started_at_utc=<UTC timestamp>
ended_at_utc=<UTC timestamp>
notes=<short summary>
```
