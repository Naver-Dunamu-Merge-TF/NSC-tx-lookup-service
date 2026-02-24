# F3-4 AKS Early Validation Track Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close F3-4 by proving AKS readiness (`provisioningState=Succeeded` + `txlookup` namespace), validating API/Consumer startup with DB/Event Hubs connectivity, and capturing in-cluster `/admin/tx/{tx_id}` `200/404` plus consumer lag/freshness evidence.

**Architecture:** Deliver F3-4 as a docs-plus-verification track. Add a dedicated runbook and evidence template, enforce required content with unit tests, and update roadmap/decision traceability. Every task is executed through a fixed subagent loop (`Implementer -> Spec Reviewer -> Code Quality Reviewer -> Fix/Re-review`) before completion.

**Tech Stack:** Python 3.11, pytest, markdown docs, bash, Azure CLI (`az`), `kubectl`.

---

## Execution Mode Decision (2026-02-24)

- Keep `writing-plans` header compatibility (`executing-plans`) for workflow consistency.
- Actual execution mode for this workstream is Subagent-Driven in the current session.
- Header line is compatibility-only; implementation/review/fix loops in this document must run in Subagent-Driven mode.

## Sources of Truth

- `.roadmap/implementation_roadmap.md`
- `.specs/backoffice_project_specs.md`
- `.specs/backoffice_data_project.md`
- `.specs/decision_open_items.md`
- `docs/ops/f3_2_slo_alerts_runbook.md`
- `docs/ops/f3_3_quality_gate_runbook.md`
- `docs/ops/f3_3_validation_evidence_template.md`

## Mandatory Subagent Loop (Per Task)

1. Dispatch `Implementer` subagent with full task text and exact file list.
2. Implementer applies minimal change set and runs task-level verification.
3. Dispatch `Spec Reviewer` subagent for SSOT/roadmap/decision compliance.
4. If spec issues exist, return to Implementer for fixes and re-run spec review.
5. Dispatch `Code Quality Reviewer` subagent only after spec review is `OK`.
6. If quality issues exist, return to Implementer for fixes and re-run quality review.
7. Mark task complete only when both reviewers return `OK`.
8. Store loop evidence under `.agents/logs/verification/<timestamp>_f3_4_<task>/`.

## Deliverables

1. `docs/ops/f3_4_aks_early_validation_runbook.md`
2. `docs/ops/f3_4_validation_evidence_template.md`
3. `tests/unit/test_f3_4_aks_early_validation_docs.py`
4. Updated F3-4 references in `.roadmap/implementation_roadmap.md`
5. F3-4 retry/escalation decision trace in `.specs/decision_open_items.md`

### Task 1: Add F3-4 docs guardrail tests and baseline artifacts

**Files:**
- Create: `tests/unit/test_f3_4_aks_early_validation_docs.py`
- Create: `docs/ops/f3_4_aks_early_validation_runbook.md`
- Create: `docs/ops/f3_4_validation_evidence_template.md`

**Step 1: Write failing docs tests**

Add assertions for required F3-4 tokens:
- `provisioningState=Succeeded`
- `txlookup` namespace
- `API/Consumer image pull`
- `DB/Event Hubs`
- `GET /admin/tx/{tx_id}`
- `200` and `404`
- `consumer lag`
- `consumer_freshness_seconds`
- `.agents/logs/verification/`

**Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_4_aks_early_validation_docs.py -x
```

Expected: `FAIL` because files/tokens are not present yet.

**Step 3: Create minimal runbook/template**

Add minimal sections only:
- scope and prerequisites
- readiness checks
- image startup smoke section
- API `200/404` smoke section
- lag/freshness evidence section

**Step 4: Re-run tests**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_4_aks_early_validation_docs.py -x
```

Expected: `PASS`.

**Step 5: Execute subagent review loop**

Archive Implementer/Spec/Quality outputs under task evidence directory.

**Step 6: Commit**

```bash
git add tests/unit/test_f3_4_aks_early_validation_docs.py docs/ops/f3_4_aks_early_validation_runbook.md docs/ops/f3_4_validation_evidence_template.md
git commit -m "docs: add f3-4 early validation baseline runbook and tests"
```

Expected: one commit containing Task 1 artifacts only.

### Task 2: Define AKS readiness and namespace preparation procedure

**Files:**
- Modify: `docs/ops/f3_4_aks_early_validation_runbook.md`
- Modify: `tests/unit/test_f3_4_aks_early_validation_docs.py`

**Step 1: Extend tests with readiness/namespace command criteria**

Require tokens:
- `az aks show -g 2dt-final-team4 -n nsc-aks-dev --query provisioningState -o tsv`
- `kubectl get ns txlookup`
- `kubectl create ns txlookup`
- readiness gate text: `provisioningState=Succeeded`

**Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_4_aks_early_validation_docs.py -x
```

Expected: `FAIL` until runbook is updated.

**Step 3: Update runbook with concrete readiness flow**

Include:
- fixed precheck order (`az login` -> AKS state -> kubeconfig -> namespace)
- namespace create-if-missing branch
- blocked handling when AKS is not `Succeeded`
- evidence file naming convention for readiness logs

**Step 4: Re-run tests**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_4_aks_early_validation_docs.py -x
```

Expected: `PASS`.

**Step 5: Execute subagent review loop**

Spec review validates roadmap F3-4 bullet alignment. Quality review validates procedural clarity.

**Step 6: Commit**

```bash
git add docs/ops/f3_4_aks_early_validation_runbook.md tests/unit/test_f3_4_aks_early_validation_docs.py
git commit -m "docs: define f3-4 aks readiness and namespace preparation flow"
```

Expected: one commit containing Task 2 artifacts only.

### Task 3: Define API/Consumer image startup smoke with dependency checks

**Files:**
- Modify: `docs/ops/f3_4_aks_early_validation_runbook.md`
- Modify: `tests/unit/test_f3_4_aks_early_validation_docs.py`

**Step 1: Extend tests with image/startup/dependency criteria**

Require tokens:
- `API_DEPLOYMENT`
- `CONSUMER_DEPLOYMENT`
- `kubectl -n txlookup set image deployment/${API_DEPLOYMENT}`
- `kubectl -n txlookup set image deployment/${CONSUMER_DEPLOYMENT}`
- `kubectl -n txlookup rollout status deployment/${API_DEPLOYMENT}`
- `kubectl -n txlookup rollout status deployment/${CONSUMER_DEPLOYMENT}`
- `DB connection`
- `Event Hubs connection`

**Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_4_aks_early_validation_docs.py -x
```

Expected: `FAIL` until startup smoke section is complete.

**Step 3: Update runbook with startup smoke flow**

Document:
- deployment name inputs (`API_DEPLOYMENT`, `CONSUMER_DEPLOYMENT`) and name precheck (`kubectl -n txlookup get deploy`)
- image tag inputs (`API_IMAGE`, `CONSUMER_IMAGE`)
- rollout success criteria
- log-based dependency checks for DB/Event Hubs
- rollback step on failed rollout/image pull

**Step 4: Re-run tests**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_4_aks_early_validation_docs.py -x
```

Expected: `PASS`.

**Step 5: Execute subagent review loop**

Spec review checks F3-4 mandatory scope. Quality review checks ambiguity in command/run conditions.

**Step 6: Commit**

```bash
git add docs/ops/f3_4_aks_early_validation_runbook.md tests/unit/test_f3_4_aks_early_validation_docs.py
git commit -m "docs: add f3-4 api consumer startup smoke and dependency checks"
```

Expected: one commit containing Task 3 artifacts only.

### Task 4: Define in-cluster API `200/404` smoke + lag/freshness validation and failure taxonomy

**Files:**
- Modify: `docs/ops/f3_4_aks_early_validation_runbook.md`
- Modify: `docs/ops/f3_4_validation_evidence_template.md`
- Modify: `tests/unit/test_f3_4_aks_early_validation_docs.py`

**Step 1: Extend tests with API and metrics evidence criteria**

Require tokens:
- `GET /admin/tx/{tx_id}`
- `returns 200`
- `returns 404`
- `consumer lag`
- `consumer_freshness_seconds`
- `failure_classification`
- `retry_at_utc`
- `unblock_criteria`

**Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_4_aks_early_validation_docs.py -x
```

Expected: `FAIL`.

**Step 3: Update runbook/template with concrete evidence contract**

Include:
- in-cluster API smoke commands and expected HTTP status checks
- lag/freshness evidence query path with fixed priority:
  - primary: Azure Monitor `AppMetrics` evidence logs using `docs/ops/f3_2_slo_alerts_runbook.md` KQL baseline
  - fallback: cluster metrics evidence only when Azure Monitor query path is unavailable; in this branch set `failure_classification=MONITORING_ACCESS_BLOCKED` and capture unblock owner/retry
- failure classes (`ENVIRONMENT_BLOCKED`, `STARTUP_FAILED`, `SMOKE_FAILED`, `METRIC_FAILED`, `MONITORING_ACCESS_BLOCKED`)
- retry policy fields (owner, retry time, unblock criteria, latest evidence path)

**Step 4: Re-run tests**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_4_aks_early_validation_docs.py -x
```

Expected: `PASS`.

**Step 5: Execute subagent review loop**

Spec review confirms SLO/freshness references align with SSOT. Quality review confirms failure taxonomy and retry policy are actionable.

**Step 6: Commit**

```bash
git add docs/ops/f3_4_aks_early_validation_runbook.md docs/ops/f3_4_validation_evidence_template.md tests/unit/test_f3_4_aks_early_validation_docs.py
git commit -m "docs: add f3-4 in-cluster smoke and failure retry evidence policy"
```

Expected: one commit containing Task 4 artifacts only.

### Task 5: Apply roadmap/decision traceability updates and run verification ladder

**Files:**
- Modify: `.roadmap/implementation_roadmap.md`
- Modify: `.specs/decision_open_items.md`
- Modify: `tests/unit/test_f3_4_aks_early_validation_docs.py`

**Step 1: Extend tests with roadmap/decision traceability assertions**

Require F3-4 section references:
- `docs/ops/f3_4_aks_early_validation_runbook.md`
- `docs/ops/f3_4_validation_evidence_template.md`
- retry/escalation decision entry in `.specs/decision_open_items.md`

**Step 2: Run test to verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_4_aks_early_validation_docs.py -x
```

Expected: `FAIL` until references are added.

**Step 3: Update roadmap and decision docs**

Document:
- F3-4 completion evidence path
- blocked handling and retry ownership
- explicit unblock criteria (`provisioningState=Succeeded`, namespace ready, API `200/404` smoke pass, lag/freshness evidence pass)

**Step 4: Re-run targeted docs test**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_4_aks_early_validation_docs.py -x
```

Expected: `PASS`.

**Step 5: Run verification ladder and store evidence**

Run:

```bash
.venv/bin/python -m py_compile $(find src -name '*.py')
.venv/bin/python -m pytest tests/unit/ -x
.venv/bin/python -m pytest --cov-fail-under=80
```

Save all logs under `.agents/logs/verification/<timestamp>_f3_4_closeout/`.

**Step 6: Execute final subagent review loop**

Final completion requires both reviewers `OK` and verification evidence present.

**Step 7: Commit**

```bash
git add .roadmap/implementation_roadmap.md .specs/decision_open_items.md docs/ops/f3_4_aks_early_validation_runbook.md docs/ops/f3_4_validation_evidence_template.md tests/unit/test_f3_4_aks_early_validation_docs.py
git commit -m "docs: finalize f3-4 aks early validation track and gate evidence policy"
```

Expected: one commit containing Task 5 artifacts only.

## Done Definition

1. All tasks complete with subagent loop evidence per task.
2. `docs/ops/f3_4_aks_early_validation_runbook.md` and `docs/ops/f3_4_validation_evidence_template.md` exist and pass docs tests.
3. Roadmap F3-4 section links to artifacts and gate criteria.
4. Decision log captures retry/escalation and unblock policy.
5. Verification evidence (`L0/L1/L2`) is stored under `.agents/logs/verification/`.

## Risks and Controls

1. AKS readiness instability delays execution.
Control: enforce blocked classification and owner-based retry policy in evidence template.
2. Startup smoke ambiguity causes false pass/fail decisions.
Control: token-checked runbook commands and explicit success criteria.
3. Metrics evidence missing or inconsistent between runs.
Control: fixed evidence schema (`command`, `exit_code`, UTC timestamp) and mandatory artifact paths.
