# F3-3 AKS Jumpbox Validation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Establish a repeatable jumpbox path for AKS private-cluster L3 validation, including mandatory teardown/deletion documentation and evidence (execution gated by explicit requester instruction).

**Architecture:** This is an operations-first delivery track: test-gated docs define the jumpbox lifecycle (provision -> access -> validate -> teardown), then an in-environment pilot run captures evidence. Every task is executed with a mandatory subagent loop (`Implementer -> Spec Reviewer -> Code Quality Reviewer -> Fix/Re-review`) so the procedure remains auditable and safe.

**Tech Stack:** Azure CLI (`az`), `kubectl`, `kubelogin`, bash, markdown docs, pytest.

---

## Execution Mode Decision (2026-02-24)

- Header compatibility keeps `executing-plans` for workflow consistency.
- Actual execution mode for this workstream is Subagent-Driven in current session.

## Sources of Truth

- `.specs/backoffice_project_specs.md`
- `.specs/backoffice_data_project.md`
- `.specs/infra/tx_lookup_azure_resource_inventory.md`
- `.specs/decision_open_items.md`
- `.roadmap/implementation_roadmap.md`
- `docs/ops/f3_3_quality_gate_runbook.md`

## Mandatory Subagent Loop (Per Task)

1. Dispatch `Implementer` subagent with full task text and file list.
2. Implementer performs minimal change set and task-level verification.
3. Dispatch `Spec Reviewer` subagent for SSOT/roadmap/decision compliance.
4. If spec issues exist, return to Implementer for fixes and re-run spec review.
5. Dispatch `Code Quality Reviewer` subagent only after spec review is `OK`.
6. If quality issues exist, return to Implementer for fixes and re-run quality review.
7. Mark task complete only when both reviewers return `OK`.
8. Store loop evidence under `.agents/logs/verification/<timestamp>_f3_3_jumpbox_<task>/`.

## Deliverables

1. Jumpbox provisioning/access runbook for AKS private cluster
2. Jumpbox teardown/deletion runbook (VM/NIC/disk/public IP cleanup)
3. Docs drift unit test coverage for jumpbox lifecycle
4. Pilot validation evidence bundle (`pass` or `blocked` with cause)
5. Roadmap/decision updates for ongoing recurring validation

## Operational Guardrails

- Jumpbox VM must be private-only (`--public-ip-address ''`)
- Access path must be Bastion or approved private connectivity
- Bastion SSH precheck is mandatory: ensure `ssh` extension is installed before `az network bastion ssh`
  - `az extension show -n ssh || az extension add -n ssh`
- All resources must be tagged with owner/purpose/ttl for cleanup traceability
- Teardown evidence is mandatory even when validation is blocked
- Teardown command execution policy: do not execute teardown until requester explicitly asks for teardown

### Task 1: Add test guardrails for jumpbox lifecycle docs

**Files:**
- Create: `tests/unit/test_f3_3_aks_jumpbox_docs.py`
- Create: `docs/ops/f3_3_aks_jumpbox_runbook.md`
- Create: `docs/ops/f3_3_aks_jumpbox_teardown_runbook.md`

**Step 1: Write failing docs tests**

Add assertions for required tokens:
- `nsc-vnet-dev`, `nsc-snet-admin`
- `Bastion`
- `--public-ip-address ''`
- `az vm create`
- `az vm delete`
- `.agents/logs/verification/`

**Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_3_aks_jumpbox_docs.py -x
```

Expected: `FAIL` because docs do not exist yet.

**Step 3: Create minimal runbook/teardown docs**

Add minimal sections and required tokens only.

**Step 4: Re-run tests**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_3_aks_jumpbox_docs.py -x
```

Expected: `PASS`.

**Step 5: Execute subagent review loop**

Archive implementer/spec/quality outputs in task evidence directory.

**Step 6: Commit**

```bash
git add tests/unit/test_f3_3_aks_jumpbox_docs.py docs/ops/f3_3_aks_jumpbox_runbook.md docs/ops/f3_3_aks_jumpbox_teardown_runbook.md
git commit -m "Document jumpbox lifecycle baseline with test guardrails"
```

Expected: one commit with Task 1 artifacts only.

### Task 2: Author secure jumpbox provisioning and AKS access procedure

**Files:**
- Modify: `docs/ops/f3_3_aks_jumpbox_runbook.md`
- Modify: `tests/unit/test_f3_3_aks_jumpbox_docs.py`

**Step 1: Extend tests with provisioning/access criteria**

Add assertions for:
- required tags (`owner`, `purpose`, `ttl`)
- `az vm create` command example in `nsc-snet-admin`
- Bastion connection path
- `kubelogin convert-kubeconfig -l azurecli`
- readiness checks (`kubectl cluster-info`, `kubectl get ns txlookup`)

**Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_3_aks_jumpbox_docs.py -x
```

Expected: `FAIL` until runbook is updated.

**Step 3: Update runbook with concrete commands**

Include:
- fixed resource names for today's run:
  - VM: `jump-aks-20260224-2dt026`
  - NIC: `nic-jump-aks-20260224-2dt026`
  - OS disk: `osdisk-jump-aks-20260224-2dt026`
  - Data disk (optional): `datadisk-jump-aks-20260224-2dt026-01`
  - tags: `owner=2dt026`, `purpose=f3-3-jumpbox`, `ttl=2026-02-24`
- provisioning command with no public IP
- Bastion SSH precheck (`az extension show -n ssh || az extension add -n ssh`)
- Bastion entry sequence
- AKS private FQDN connectivity checks
- evidence file naming convention

**Step 4: Re-run tests**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_3_aks_jumpbox_docs.py -x
```

Expected: `PASS`.

**Step 5: Execute subagent review loop**

Spec review checks security guardrails. Quality review checks command clarity and rollback notes.

**Step 6: Commit**

```bash
git add docs/ops/f3_3_aks_jumpbox_runbook.md tests/unit/test_f3_3_aks_jumpbox_docs.py
git commit -m "Define secure jumpbox provisioning and AKS access procedure"
```

Expected: one commit with Task 2 artifacts only.

### Task 3: Execute one pilot jumpbox validation run and archive evidence

**Files:**
- Modify: `docs/ops/f3_3_aks_jumpbox_runbook.md`
- Modify: `docs/ops/f3_3_aks_jumpbox_teardown_runbook.md`
- Create: `.agents/logs/verification/<timestamp>_f3_3_jumpbox_pilot/` (runtime evidence)

**Step 1: Prepare pilot evidence directory**

Create runtime evidence folder and log commands with:
- `command`
- `exit_code`
- `UTC timestamp`

**Step 2: Execute provisioning and access commands**

Run provisioning + Bastion/jumpbox access checks from Task 2 runbook.
Include Bastion SSH precheck before access command:

```bash
az extension show -n ssh || az extension add -n ssh
```

**Step 3: Execute AKS readiness checks and L3 precheck**

Run:
- `az aks show ... --query provisioningState`
- `kubectl cluster-info`
- `kubectl get ns txlookup`

**Step 4: Branch outcome handling**

- Branch A (`READY`): continue with L3 scenario commands and save `*_l3_pass/` logs.
- Branch B (`BLOCKED`): save blocked cause logs and create summary with owner/retry/unblock criteria.

**Step 5: Execute teardown commands only after explicit requester instruction**

Run teardown from `docs/ops/f3_3_aks_jumpbox_teardown_runbook.md` only when requester explicitly instructs teardown:
- delete VM
- delete NIC
- delete managed OS disk and attached data disk(s) if present
- run residual resource scan by tag and store output

If explicit teardown instruction is not given:
- record `teardown_pending=true` in pilot summary evidence
- keep resource inventory snapshot in evidence bundle

Expected after teardown execution: zero residual jumpbox resources.

**Step 6: Execute subagent review loop**

Spec review verifies evidence contract completeness. Quality review verifies log readability and reproducibility.

**Step 7: Commit docs-only changes if runbook wording changed**

```bash
git add docs/ops/f3_3_aks_jumpbox_runbook.md docs/ops/f3_3_aks_jumpbox_teardown_runbook.md
# Commit only if documentation changed in this task.
```

If no documentation changes were made, skip commit and write `no_doc_change=true` in pilot summary evidence.

Expected: no source-code changes; evidence stored under `.agents/logs/verification/`.

### Task 4: Document VM deletion and enforce teardown evidence

**Files:**
- Modify: `docs/ops/f3_3_aks_jumpbox_teardown_runbook.md`
- Modify: `tests/unit/test_f3_3_aks_jumpbox_docs.py`

**Step 1: Extend tests with mandatory teardown content**

Add assertions for:
- `az vm delete --yes`
- `az network nic delete`
- `az disk delete --yes`
- orphan resource scan (`az resource list --tag purpose=f3-3-jumpbox`)
- teardown evidence summary format

**Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_3_aks_jumpbox_docs.py -x
```

Expected: `FAIL` until teardown doc is detailed.

**Step 3: Update teardown runbook**

Document:
- deletion order (VM -> NIC -> disk -> optional PIP)
- deletion target names for today's run:
  - `jump-aks-20260224-2dt026`
  - `nic-jump-aks-20260224-2dt026`
  - `osdisk-jump-aks-20260224-2dt026`
  - `datadisk-jump-aks-20260224-2dt026-01` (if created)
- verification queries for zero residual resources
- failure handling if delete returns conflict/lock
- mandatory evidence bundle path

**Step 4: Re-run tests**

Run:

```bash
.venv/bin/python -m pytest tests/unit/test_f3_3_aks_jumpbox_docs.py -x
```

Expected: `PASS`.

**Step 5: Execute subagent review loop**

Spec review checks deletion completeness. Quality review checks idempotent cleanup instructions.

**Step 6: Commit**

```bash
git add docs/ops/f3_3_aks_jumpbox_teardown_runbook.md tests/unit/test_f3_3_aks_jumpbox_docs.py
git commit -m "Add mandatory jumpbox teardown and cleanup evidence procedure"
```

Expected: one commit with Task 4 artifacts only.

### Task 5: Wire roadmap/decision updates and run final verification gates

**Files:**
- Modify: `.roadmap/implementation_roadmap.md`
- Modify: `.specs/decision_open_items.md`
- Modify: `.specs/infra/tx_lookup_azure_resource_inventory.md`
- Modify: `docs/ops/f3_3_quality_gate_runbook.md`

**Step 1: Update roadmap references**

Add links to jumpbox runbook + teardown runbook and recurring validation cadence.

**Step 2: Update decision/inventory docs**

Document jumpbox policy:
- when jumpbox is allowed
- teardown SLA (same day)
- required evidence for blocked/pass outcomes

**Step 3: Update quality gate runbook integration**

Update `docs/ops/f3_3_quality_gate_runbook.md` with:
- jumpbox-required path for private-cluster validation
- teardown runbook link and same-day cleanup rule
- recurring cadence note for periodic re-validation

**Step 4: Run verification ladder for touched scope**

Run and store logs:

```bash
.venv/bin/python -m py_compile $(find src -name '*.py')
.venv/bin/python -m pytest tests/unit/test_f3_3_aks_jumpbox_docs.py -x
.venv/bin/python -m pytest tests/unit/ -x
.venv/bin/python -m pytest --cov-fail-under=80
```

**Step 5: Execute final subagent review loop**

Final approval requires no unresolved critical/important findings.

**Step 6: Commit**

```bash
git add .roadmap/implementation_roadmap.md .specs/decision_open_items.md .specs/infra/tx_lookup_azure_resource_inventory.md docs/ops/f3_3_quality_gate_runbook.md tests/unit/test_f3_3_aks_jumpbox_docs.py
git commit -m "Integrate jumpbox validation policy into roadmap and SSOT references"
```

Expected: one commit with Task 5 artifacts only.

## Done Definition

1. Jumpbox provisioning/access runbook is test-gated and review-approved.
2. VM deletion/teardown runbook is test-gated and review-approved.
3. Pilot evidence exists under `.agents/logs/verification/` with pass or blocked summary.
4. Roadmap + decision + infra docs reflect recurring jumpbox validation policy.
5. L0/L1/L2 verification logs exist and pass.
6. If pilot is blocked, defer owner/retry/unblock criteria are documented.
7. If teardown is not explicitly instructed, pilot summary includes `teardown_pending=true`.

## Pilot Learning (2026-02-24)

- Learned failure during Bastion access:
  - `az network bastion ssh` failed with `exit_code: 1`
  - error: `The extension ssh is not installed`
- Action:
  - add Bastion SSH precheck before access:
    - `az extension show -n ssh || az extension add -n ssh`

## Risks and Controls

1. Private DNS/VNet path still blocks kubectl from jumpbox.
Control: keep blocked evidence template mandatory and escalate network owner.
2. Jumpbox resource sprawl increases cost/security risk.
Control: mandatory TTL tags + teardown runbook + residual resource scan.
3. Docs drift from actual operator commands.
Control: token-based docs unit tests + subagent spec review on every task.
