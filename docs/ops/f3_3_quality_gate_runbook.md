# F3-3 Quality Gate Runbook (Dev)

## 1) Scope

- Environment: `dev` (`2dt-final-team4`)
- Goal: close F3-3 by fixing repeatable quality-gate operation and evidence policy
- Hard rule: E2 entry remains blocked until at least one AKS `in-cluster` L3 pass evidence bundle exists
- Private AKS `in-cluster` validation uses the jumpbox-required path:
  - `docs/ops/f3_3_aks_jumpbox_runbook.md`
  - `docs/ops/f3_3_aks_jumpbox_teardown_runbook.md`
- Teardown is mandatory with same-day cleanup for every jumpbox run, including blocked runs.
- Teardown command execution requires explicit requester instruction; until then, evidence must record `teardown_pending=true`.

## 2) L2 Gate Cadence and Handling

Fixed L2 command:

```bash
.venv/bin/python -m pytest --cov-fail-under=80
```

Cadence:

- Daily working-day execution during F3 closeout
- Mandatory execution before closeout approval request
- Recurring re-validation cadence after closeout: at least weekly or before E2 entry gate checks

Pass/Fail handling:

- `PASS`: archive command output and update checklist status to `READY_FOR_REVIEW`
- `FAIL`: stop approval flow, open fix item, re-run until green

## 3) L3 Scenario Selection Rules

L3 smoke selection is fixed to admin lookup behaviors with highest regression risk:

- Pairing path (`pairing_status` complete/incomplete/unknown)
- Status-change freshness path (event update reflected in serving query)

Baseline scenario specification:

- `docs/ops/f3_3_l3_cluster_smoke_scenarios.md`

Each cycle must include at least one pairing-focused scenario and one status-change scenario.

## 4) AKS Prerequisite Checks

Before running L3 scenarios:

- `az aks show` must report `provisioningState=Succeeded`
- AKS cluster is queryable from `az`/`kubectl` without auth error
- target namespace `txlookup` exists and namespace readiness is confirmed (`kubectl get ns txlookup`)
- API endpoint routing from cluster context is reachable

If prerequisite fails, treat L3 as blocked and follow conditional-allow policy (`DEC-226` traceability).

## 4.1) Jumpbox Required Path for Private-Cluster Validation

For private-cluster validation where local runner cannot resolve AKS private DNS, use:

1. Provision and access jumpbox via `docs/ops/f3_3_aks_jumpbox_runbook.md`
2. Execute AKS readiness and L3 smoke checks from the jumpbox
3. Run mandatory teardown via `docs/ops/f3_3_aks_jumpbox_teardown_runbook.md`

This path is not optional for private-cluster validation when direct access is unavailable.

## 5) Evidence Storage Policy

All F3-3 evidence is stored under:

`.agents/logs/verification/`

Naming convention:

- Task loop: `.agents/logs/verification/<timestamp>_f3_3_<task>/`
- L3 pass bundle: `.agents/logs/verification/<timestamp>_f3_3_l3_pass/`
- L3 blocked bundle: `.agents/logs/verification/<timestamp>_f3_3_l3_blocked/`

Minimum files per task loop:

- test execution log
- spec review result
- code quality review result
- rerun log when fixes were needed

Command capture format (mandatory for each evidence record):

- `command`: executed shell command
- `exit_code`: numeric exit status
- `UTC timestamp`: execution time in UTC ISO8601

The minimum evidence for one successful in-cluster run:

- `az aks show` output proving `provisioningState=Succeeded`
- `kubectl` output proving `txlookup` namespace readiness
- logs for `L3-SMOKE-01` to `L3-SMOKE-04`
- summary note that marks the bundle as a successful in-cluster run

Template reference:

- `docs/ops/f3_3_validation_evidence_template.md`

## 6) Verification Execution Flow

Run sequence:

1. L0
   - `.venv/bin/python -m py_compile $(find src -name '*.py')`
2. L1
   - `.venv/bin/python -m pytest tests/unit/ -x`
3. L2
   - `.venv/bin/python -m pytest --cov-fail-under=80`
4. L3 readiness probe and branch decision
   - `az aks show ... --query provisioningState -o tsv`
   - `kubectl get ns txlookup`
   - `kubectl -n txlookup get pods`

Branch A (`AKS ready`):

- Save scenario execution logs under `.agents/logs/verification/<timestamp>_f3_3_l3_pass/`
- Mark checklist as `GO` only when all mandatory evidence is complete

Branch B (`AKS not ready`, conditional allow):

- Save readiness failure logs under `.agents/logs/verification/<timestamp>_f3_3_l3_blocked/`
- Record defer owner, retry date, unblock criteria
- Include jumpbox teardown evidence proving same-day cleanup completion
- Update checklist status to `CONDITIONAL (L3 deferred by DEC-226)`
- Keep E2 entry hard-blocked until Branch A pass evidence exists

## 7) Latest Execution Snapshot (2026-02-24 UTC)

- L0/L1/L2 logs: `.agents/logs/verification/20260223_175121_f3_3_task5/`
- L3 blocked logs: `.agents/logs/verification/20260223_175150_f3_3_l3_blocked/`
- Jumpbox pilot evidence: `.agents/logs/verification/20260224_012413_f3_3_jumpbox_pilot/`
- Observed readiness state:
  - `provisioningState=Canceled`
  - `kubectl` failed private DNS resolution from current runner
- Current closeout status: `CONDITIONAL (L3 deferred by DEC-226)`
