# F3-3 Validation Evidence Template

Use this template when recording L3 execution results for F3-3.

## 1) Run Metadata

| Field | Value |
| --- | --- |
| Run ID | `<timestamp>_f3_3_l3_pass` or `<timestamp>_f3_3_l3_blocked` |
| Environment | `dev` |
| Owner | `<name>` |
| UTC timestamp | `<YYYY-MM-DDTHH:MM:SSZ>` |
| Decision Ref | `DEC-226` |

## 2) AKS readiness

Record readiness checks before any scenario execution:

| Check | Result | Evidence file |
| --- | --- | --- |
| `az aks show` includes `provisioningState=Succeeded` | `PASS/FAIL` | `<file>` |
| `kubectl get ns txlookup` confirms `txlookup namespace ready` | `PASS/FAIL` | `<file>` |
| `kubectl -n txlookup get pods` core workload ready | `PASS/FAIL` | `<file>` |

## 3) Command Capture Format

Every command log line must include:

- `command`
- `exit_code`
- `UTC timestamp`

Example:

```text
command=kubectl -n txlookup get pods
exit_code=0
UTC timestamp=2026-02-24T09:00:00Z
```

## 4) Scenario Results

| Scenario | Result | Evidence file |
| --- | --- | --- |
| `L3-SMOKE-01` | `PASS/FAIL` | `<file>` |
| `L3-SMOKE-02` | `PASS/FAIL` | `<file>` |
| `L3-SMOKE-03` | `PASS/FAIL` | `<file>` |
| `L3-SMOKE-04` | `PASS/FAIL` | `<file>` |

## 5) minimum evidence set

The minimum evidence set for closure is:

1. AKS readiness logs (`provisioningState=Succeeded`, namespace readiness)
2. Four scenario execution logs
3. Final run summary (`PASS` or conditional defer)

## 6) Failure Classification and Escalation

If any required item fails:

- classify as `ENVIRONMENT_BLOCKED`, `SCENARIO_FAILED`, or `DATA_PREP_FAILED`
- assign escalation owner
- set next retry date
- document unblock criteria:
  - `provisioningState=Succeeded`
  - `txlookup namespace ready`
