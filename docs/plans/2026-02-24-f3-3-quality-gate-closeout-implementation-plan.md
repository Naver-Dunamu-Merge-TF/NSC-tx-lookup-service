# F3-3 Quality Gate Closeout Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close F3-3 by fixing L2/L3 gate operations, completing at least one AKS in-cluster validation run, and publishing an approval-ready closeout checklist for Contract/Alerts/Tests.

**Architecture:** Treat F3-3 as a documentation-plus-verification delivery track. Every task is executed with a mandatory subagent loop (`Implementer -> Spec Reviewer -> Code Quality Reviewer -> Fix/Re-review`) so each artifact is both SSOT-compliant and operationally actionable before it is marked complete.

**Tech Stack:** Python 3.11, pytest, markdown docs, bash, Azure CLI (`az`), `kubectl`, Docker Compose.

---

## Execution Mode Decision (2026-02-24)

- Decision (item #1): keep `writing-plans` header compatibility (`executing-plans`) for workflow/tooling consistency.
- Operational mode for this workstream: Subagent-Driven in current session (`Implementer -> Spec Reviewer -> Code Quality Reviewer -> Fix/Re-review`).

## Sources of Truth

- `.specs/backoffice_project_specs.md`
- `.specs/backoffice_data_project.md`
- `.specs/decision_open_items.md`
- `.specs/infra/tx_lookup_azure_resource_inventory.md`
- `.roadmap/implementation_roadmap.md`

## Mandatory Subagent Loop (Per Task)

1. Dispatch `Implementer` subagent with full task text and file list.
2. Implementer makes the minimal change set and runs task-level tests.
3. Dispatch `Spec Reviewer` subagent to verify SSOT/roadmap/decision compliance.
4. If spec gaps exist, return to Implementer for fixes, then re-run Spec Review.
5. Dispatch `Code Quality Reviewer` subagent only after spec review is `OK`.
6. If quality issues exist, return to Implementer for fixes, then re-run Quality Review.
7. Mark task complete only when both reviewers return `OK`.
8. Store execution evidence under `.agents/logs/verification/<timestamp>_f3_3_<task>/`.

## Deliverables

1. F3-3 quality gate runbook (L2 schedule + L3 criteria + evidence policy)
2. L3 in-cluster smoke scenario spec (pairing/status-change focused)
3. F3 closeout checklist (Contract/Alerts/Tests integrated)
4. Verification evidence logs (L0/L1/L2 mandatory, L3 when environment is ready)

## Conditional Acceptance Policy (Decision #2)

- Conditional allow is permitted when AKS is not ready.
- Scope of conditional allow: F3-3 documentation/process completion only.
- Hard gate: E2 entry is blocked until one successful AKS in-cluster L3 evidence bundle exists.
- Minimum defer evidence: readiness failure logs, owner, retry date, unblock criteria, and `DEC-226` reference.

### Task 1: Add a F3-3 quality gate runbook

**Files:**
- Create: `docs/ops/f3_3_quality_gate_runbook.md`
- Create: `tests/unit/test_f3_3_quality_gate_docs.py`
- Modify: `.roadmap/implementation_roadmap.md`

**Step 1: Write failing docs tests**

Add tests that assert:
- runbook file exists
- runbook includes L2 command: `.venv/bin/python -m pytest --cov-fail-under=80`
- runbook includes L3 in-cluster execution requirement
- runbook includes evidence path policy under `.agents/logs/verification/`

**Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_3_quality_gate_docs.py -x
```

Expected: `FAIL` because file/tokens do not exist yet.

**Step 3: Create minimal runbook content**

Document:
- fixed L2 cadence and pass/fail handling
- L3 scenario selection rules (pairing + status-change)
- AKS prerequisite checks
- evidence storage format and naming

**Step 4: Re-run tests**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_3_quality_gate_docs.py -x
```

Expected: `PASS`.

**Step 5: Execute subagent review loop**

Use mandatory loop and archive reviewer outputs in task evidence directory.

**Step 6: Commit**

Run:

```bash
git add docs/ops/f3_3_quality_gate_runbook.md tests/unit/test_f3_3_quality_gate_docs.py .roadmap/implementation_roadmap.md
git commit -m "docs: add f3-3 quality gate runbook baseline"
```

Expected: one commit containing only Task 1 artifacts.

### Task 2: Freeze L3 in-cluster smoke scenario baseline

**Files:**
- Create: `docs/ops/f3_3_l3_cluster_smoke_scenarios.md`
- Modify: `docs/ops/f3_3_quality_gate_runbook.md`
- Modify: `tests/unit/test_f3_3_quality_gate_docs.py`

**Step 1: Write failing test assertions**

Add checks for required scenario IDs and acceptance criteria:
- `L3-SMOKE-01`: `/admin/tx/{tx_id}` returns `200`
- `L3-SMOKE-02`: `/admin/tx/{tx_id}` returns `404` when missing
- `L3-SMOKE-03`: pairing incomplete path with expected `pairing_status`
- `L3-SMOKE-04`: status-change freshness verification path

**Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_3_quality_gate_docs.py -x
```

Expected: `FAIL` until scenario spec is created.

**Step 3: Author scenario spec**

Define for each scenario:
- prerequisites
- input/event setup
- execution command(s)
- expected API/metric result
- pass/fail criteria

**Step 4: Re-run tests**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_3_quality_gate_docs.py -x
```

Expected: `PASS`.

**Step 5: Execute subagent review loop**

Spec review validates SSOT behavior; quality review validates ambiguity/risk removal.

**Step 6: Commit**

Run:

```bash
git add docs/ops/f3_3_l3_cluster_smoke_scenarios.md docs/ops/f3_3_quality_gate_runbook.md tests/unit/test_f3_3_quality_gate_docs.py
git commit -m "docs: define f3-3 l3 cluster smoke baseline scenarios"
```

Expected: one commit containing only Task 2 artifacts.

### Task 3: Define AKS validation execution and evidence contract

**Files:**
- Modify: `docs/ops/f3_3_quality_gate_runbook.md`
- Create: `docs/ops/f3_3_validation_evidence_template.md`
- Modify: `.specs/infra/tx_lookup_azure_resource_inventory.md`

**Step 1: Write failing tests for evidence requirements**

Add assertions that docs include:
- AKS readiness checks (`provisioningState`, namespace readiness)
- command capture format (`command`, `exit_code`, UTC timestamp)
- minimum evidence set for one successful in-cluster run

**Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_3_quality_gate_docs.py -x
```

Expected: `FAIL`.

**Step 3: Write evidence template and runbook section**

Add:
- evidence checklist table
- incident classification for failed run
- retry gate and escalation owner

**Step 4: Re-run tests**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_3_quality_gate_docs.py -x
```

Expected: `PASS`.

**Step 5: Execute subagent review loop**

Store reviewer approvals in the task evidence directory.

**Step 6: Commit**

Run:

```bash
git add docs/ops/f3_3_quality_gate_runbook.md docs/ops/f3_3_validation_evidence_template.md .specs/infra/tx_lookup_azure_resource_inventory.md tests/unit/test_f3_3_quality_gate_docs.py
git commit -m "docs: add f3-3 aks evidence contract and template"
```

Expected: one commit containing only Task 3 artifacts.

### Task 4: Publish F3 completion checklist document

**Files:**
- Create: `docs/ops/f3_3_closeout_checklist.md`
- Modify: `.roadmap/implementation_roadmap.md`
- Modify: `.specs/decision_open_items.md`
- Modify: `tests/unit/test_f3_3_quality_gate_docs.py`

**Step 1: Write failing checklist test assertions**

Require checklist sections:
- Contract evidence (F3-1 references)
- Alerts evidence (F3-2 references)
- Test evidence (F3-3 L2/L3 references)
- approval sign-off fields (owner/date/result)

**Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_3_quality_gate_docs.py -x
```

Expected: `FAIL`.

**Step 3: Draft checklist and wire references**

Checklist must include exact artifact links and go/no-go decision rule for F3 completion.

**Step 4: Re-run tests**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_3_quality_gate_docs.py -x
```

Expected: `PASS`.

**Step 5: Execute subagent review loop**

Only complete when both reviewers approve no missing gates.

**Step 6: Commit**

Run:

```bash
git add docs/ops/f3_3_closeout_checklist.md .roadmap/implementation_roadmap.md .specs/decision_open_items.md tests/unit/test_f3_3_quality_gate_docs.py
git commit -m "docs: add f3-3 closeout checklist and gate references"
```

Expected: one commit containing only Task 4 artifacts.

### Task 5: Verification and gate evidence

**Files:**
- Modify: `.roadmap/implementation_roadmap.md`
- Modify: `docs/ops/f3_3_quality_gate_runbook.md`

**Step 1: L0 verification**

Run:

```bash
.venv/bin/python -m py_compile $(find src -name '*.py')
```

Save log in `.agents/logs/verification/`.

**Step 2: L1 verification**

Run:

```bash
.venv/bin/python -m pytest tests/unit/ -x
```

Save log in `.agents/logs/verification/`.

**Step 3: L2 verification**

Run:

```bash
.venv/bin/python -m pytest --cov-fail-under=80
```

Save log in `.agents/logs/verification/`.

**Step 4: L3 verification (conditional-allow policy)**

Branch A (`AKS ready`):
- Run L3 scenario set from `docs/ops/f3_3_l3_cluster_smoke_scenarios.md`.
- Save pass evidence under `.agents/logs/verification/<timestamp>_f3_3_l3_pass/`.

Branch B (`AKS not ready`, conditional allow):
- Capture readiness failure evidence (`az aks show` provisioning state, `kubectl` namespace readiness) under `.agents/logs/verification/<timestamp>_f3_3_l3_blocked/`.
- Record defer owner, next retry date, and unblock criteria (`provisioningState=Succeeded` + `txlookup` namespace ready).
- Update closeout checklist status as `CONDITIONAL (L3 deferred by DEC-226)`.
- Keep E2 entry hard-blocked until Branch A pass evidence exists.

**Step 5: Execute final subagent review loop**

Final pass requires:
- spec review: all F3-3 gates satisfied
- quality review: no unresolved critical/important findings

**Step 6: Commit**

Run:

```bash
git add .roadmap/implementation_roadmap.md docs/ops/f3_3_quality_gate_runbook.md docs/ops/f3_3_closeout_checklist.md
git commit -m "docs: finalize f3-3 verification and conditional gate policy"
```

Expected: one commit containing only Task 5 artifacts.

## Done Definition

1. All tasks above are complete with reviewer approvals logged.
2. L0/L1/L2 logs exist under `.agents/logs/verification/`.
3. If AKS is ready, at least one successful AKS in-cluster L3 evidence bundle exists.
4. If AKS is not ready, conditional defer bundle exists with owner/date/retry and `DEC-226` traceability.
5. E2 entry cannot be approved until the successful L3 evidence bundle is uploaded.
6. `docs/ops/f3_3_closeout_checklist.md` is ready for F3 completion decision.

## Risks and Controls

1. AKS readiness instability blocks L3 execution.
Control: keep runbook retry/escalation criteria explicit and preserve partial evidence.
2. Docs drift from SSOT decisions.
Control: spec-review gate is mandatory before quality review for every task.
3. Evidence incompleteness causes non-auditable closure.
Control: use the evidence template and required token checks in docs tests.
