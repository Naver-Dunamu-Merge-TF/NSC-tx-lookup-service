# F3-4 Runtime Closeout Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close remaining F3-4 runtime gates by proving Consumer startup (DB/Event Hubs connectivity), running in-cluster `/admin/tx/{tx_id}` `200/404` smoke, and capturing consumer lag/freshness evidence so roadmap checkboxes can move from `PARTIAL` to complete.

**Architecture:** Keep docs/test contracts already merged as fixed baseline, then execute runtime validation on private AKS through jumpbox path only. Each task follows a mandatory subagent loop (`Implementer -> Spec Reviewer -> Code Quality Reviewer -> Fix/Re-review`) and stores evidence under `.agents/logs/verification/`.

**Tech Stack:** Azure CLI (`az`), jumpbox VM run-command, `kubectl`, bash, pytest, markdown docs.

---

## Execution Scope (Important)

- This plan is for runtime closeout only (`task2/task3` in roadmap F3-4).
- Do not re-open completed document-contract tasks unless runtime evidence reveals a spec mismatch.
- Private AKS assumption is fixed; direct local `kubectl` path is non-goal.

## Sources of Truth

- `.roadmap/implementation_roadmap.md`
- `.specs/decision_open_items.md` (`DEC-237`)
- `docs/ops/f3_4_aks_early_validation_runbook.md`
- `docs/ops/f3_4_validation_evidence_template.md`
- `docs/ops/f3_3_aks_jumpbox_runbook.md`
- `docs/ops/f3_2_slo_alerts_runbook.md`

## Mandatory Subagent Loop (Per Task)

1. Dispatch `Implementer` subagent with full task text and target files/commands.
2. Implementer applies minimal change or executes command sequence and captures raw outputs.
3. Dispatch `Spec Reviewer` subagent for SSOT/roadmap/decision compliance.
4. If spec issues exist, return to Implementer for fixes and re-run spec review.
5. Dispatch `Code Quality Reviewer` subagent only after spec review is `OK`.
6. If quality issues exist, return to Implementer for fixes and re-run quality review.
7. Mark task complete only when both reviewers return `OK`.
8. Store loop evidence under `.agents/logs/verification/<timestamp>_f3_4_runtime_<task>/`.

## Deliverables

1. Runtime evidence bundle proving:
   - consumer startup with DB/Event Hubs connectivity
   - in-cluster API `200/404` smoke
   - lag/freshness evidence
2. Updated roadmap F3-4 checkbox status from `PARTIAL` to closeout-ready state (if all runtime gates pass).
3. Updated runbook/template only when runtime execution reveals missing/incorrect procedure text.

### Task 1: Freeze runtime baseline and evidence directory contract

**Files:**
- Modify: `.roadmap/implementation_roadmap.md` (only if baseline status text is stale)
- Create: `.agents/logs/verification/<timestamp>_f3_4_runtime_closeout/` (runtime)

**Step 1: Snapshot AKS + namespace + existing workloads**

Run (via jumpbox path):

```bash
SCRIPT=$(cat <<'EOF'
set -eu
sudo -u azureuser -H bash -lc 'kubectl get ns txlookup -o wide'
sudo -u azureuser -H bash -lc 'kubectl get deploy,svc -n txlookup -o wide'
sudo -u azureuser -H bash -lc 'kubectl get pods -A -o wide | grep -Ei "txlookup|tx-lookup|consumer|langfuse" || true'
EOF
)
az vm run-command invoke -g 2dt-final-team4 -n jump-aks-20260224-2dt026 \
  --command-id RunShellScript \
  --scripts "$SCRIPT"
```

**Step 2: Record evidence set names**

Minimum files in runtime bundle:
- `01_aks_namespace_state.log`
- `02_consumer_rollout.log`
- `03_consumer_db_connectivity.log`
- `04_consumer_eventhubs_connectivity.log`
- `05_api_smoke_404.log`
- `06_api_smoke_200.log`
- `07_consumer_lag.log`
- `08_consumer_freshness.log`
- `99_f3_4_runtime_summary.md`

**Step 3: Execute subagent review loop**

Require explicit reviewer confirmation that evidence file contract is complete before Task 2.

### Task 2: Bring up Consumer workload and validate dependency connectivity

**Files:**
- Modify (if needed): `docs/ops/f3_4_aks_early_validation_runbook.md`
- Modify (if needed): `docs/ops/f3_4_validation_evidence_template.md`
- Create runtime logs: `.agents/logs/verification/<timestamp>_f3_4_runtime_closeout/02~04_*.log`

**Step 1: Identify actual consumer workload source**

Resolve deterministic source in this fixed order:
1. Live deployment source:
   - `kubectl -n txlookup get deploy txlookup-consumer -o yaml > 02_consumer_source_live.yaml`
2. Repository source:
   - `rg --files | rg 'txlookup-consumer|consumer.*deploy|consumer.*k8s' > 02_consumer_source_repo.txt`
3. If 1 and 2 are both unavailable, classify `ENVIRONMENT_BLOCKED` and stop closeout.

If intentionally deferred, stop and update roadmap/status memo with explicit decision reference.

**Step 2: Execute consumer rollout/startup**

Use pinned runtime contract:

```bash
API_IMAGE=$(kubectl -n txlookup get deploy tx-lookup-api -o jsonpath='{.spec.template.spec.containers[0].image}')
API_TAG="${API_IMAGE##*:}"
CONSUMER_IMAGE="nscacrdevw4mlu8.azurecr.io/txlookup/consumer:${API_TAG}"
TAG_COUNT=$(az acr repository show-tags -n nscacrdevw4mlu8 --repository txlookup/consumer --query "[?@=='${API_TAG}'] | length(@)" -o tsv)
test "$TAG_COUNT" -ge 1
```

If `TAG_COUNT` is `0`, classify `ENVIRONMENT_BLOCKED` and stop closeout.

If deployment exists:
- `kubectl -n txlookup set image deployment/txlookup-consumer consumer=${CONSUMER_IMAGE}`

If deployment does not exist, bootstrap minimal deployment:

```bash
kubectl -n txlookup create deployment txlookup-consumer --image="${CONSUMER_IMAGE}" --dry-run=client -o yaml > /tmp/txlookup-consumer.yaml
kubectl -n txlookup set env --local -f /tmp/txlookup-consumer.yaml --from=secret/txlookup-api-env SERVICE_NAME=txlookup-consumer -o yaml > /tmp/txlookup-consumer.env.yaml
kubectl apply -f /tmp/txlookup-consumer.env.yaml
kubectl -n txlookup patch deploy txlookup-consumer --type='json' -p='[{"op":"add","path":"/spec/template/spec/containers/0/command","value":["python","-m","src.consumer.main","run"]}]'
```

Wait for rollout:
- `kubectl -n txlookup rollout status deploy/txlookup-consumer --timeout=180s`

**Step 3: Validate DB/Event Hubs connectivity from consumer logs**

Capture deterministic evidence:

```bash
kubectl -n txlookup logs deploy/txlookup-consumer --tail=400 > 03_consumer_db_connectivity.log
kubectl -n txlookup logs deploy/txlookup-consumer --tail=400 > 04_consumer_eventhubs_connectivity.log
```

DB connectivity check:

```bash
kubectl -n txlookup exec deploy/txlookup-consumer -- python - <<'PY'
import os
from sqlalchemy import create_engine, text
url = os.environ["DATABASE_URL"]
engine = create_engine(url)
with engine.connect() as conn:
    conn.execute(text("SELECT 1"))
print("db_connectivity_ok")
PY
```

Event Hubs connectivity check:

```bash
kubectl -n txlookup exec deploy/txlookup-consumer -- \
  python -c 'import socket; s=socket.create_connection(("nsc-evh-dev.servicebus.windows.net", 9093), timeout=5); s.close(); print("eventhubs_tcp_ok")'
```

**Step 4: Branch policy**

- `PASS`: proceed to Task 3.
- `BLOCKED`: classify using `DEC-237` (`STARTUP_FAILED` or `ENVIRONMENT_BLOCKED`), write retry owner/date/unblock criteria, stop closeout.

**Step 5: Execute subagent review loop**

Reviewers must verify connectivity evidence lines are explicit, not inferred.

### Task 3: Run in-cluster API smoke (`404` then `200`)

**Files:**
- Create runtime logs: `.agents/logs/verification/<timestamp>_f3_4_runtime_closeout/05~06_*.log`
- Modify (if needed): `docs/ops/f3_4_aks_early_validation_runbook.md`

**Step 1: Execute `404` smoke**

Run in cluster context (jumpbox):

```bash
curl -sS -o /tmp/f3_4_tx_404.json -w '%{http_code}\n' \
  "http://tx-lookup-api.txlookup.svc.cluster.local:8000/admin/tx/missing-tx-id"
```

Expected HTTP code: `404`.

**Step 2: Execute `200` smoke**

Resolve known `tx_id` deterministically from DB:

```bash
KNOWN_TX_ID=$(kubectl -n txlookup exec deploy/txlookup-postgres -- \
  psql -U bo -d bo -At -c "select tx_id from bo.ledger_entries order by event_time desc limit 1;")
test -n "$KNOWN_TX_ID"
```

Run `200` smoke with resolved ID:

```bash
curl -sS -o /tmp/f3_4_tx_200.json -w '%{http_code}\n' \
  "http://tx-lookup-api.txlookup.svc.cluster.local:8000/admin/tx/${KNOWN_TX_ID}"
```

Expected HTTP code: `200`.

**Step 3: Capture outputs and payload excerpts**

Write response code + minimal payload summary to evidence logs.

**Step 4: Execute subagent review loop**

Spec review must verify this exactly matches roadmap bullet (`200/404`).

### Task 4: Capture consumer lag/freshness evidence with primary/fallback policy

**Files:**
- Create runtime logs: `.agents/logs/verification/<timestamp>_f3_4_runtime_closeout/07~08_*.log`
- Modify (if needed): `docs/ops/f3_4_aks_early_validation_runbook.md`

**Step 1: Primary path (Azure Monitor AppMetrics)**

Run KQL per `docs/ops/f3_2_slo_alerts_runbook.md` baseline for:
- `consumer_kafka_lag`
- `consumer_freshness_seconds`

Lag query (primary):

```kql
AppMetrics
| where Name == "consumer_kafka_lag"
| summarize max_lag=max(Max) by bin(TimeGenerated, 5m)
| order by TimeGenerated desc
```

Freshness query (primary):

```kql
AppMetrics
| where Name == "consumer_freshness_seconds"
| summarize max_freshness=max(Max) by bin(TimeGenerated, 5m)
| order by TimeGenerated desc
```

Pass contract:
- both queries must return non-empty rows in the target time window
- freshness must satisfy SLO threshold (`max_freshness <= 5s` at closeout window)

**Step 2: Fallback path**

If AppMetrics query path is unavailable:
- classify `failure_classification=MONITORING_ACCESS_BLOCKED`
- record retry owner/date/unblock criteria
- keep F3-4 status as partial

**Step 3: Execute subagent review loop**

Reviewers verify primary/fallback branch handling is explicitly evidenced.

### Task 5: Closeout decision and roadmap check updates

**Files:**
- Modify: `.roadmap/implementation_roadmap.md`
- Modify (only if policy wording changed): `.specs/decision_open_items.md`
- Modify runtime summary: `.agents/logs/verification/<timestamp>_f3_4_runtime_closeout/99_f3_4_runtime_summary.md`

**Step 1: Evaluate closeout gate**

All below must be true:
1. Consumer startup + DB/Event Hubs connectivity proven
2. `/admin/tx/{tx_id}` `404` and `200` smoke pass
3. lag/freshness evidence pass (blocked classification is not pass for closeout)

**Step 2: Update roadmap checkboxes**

- If all pass: check remaining F3-4 items and set status memo to complete.
- If blocked: keep partial and include explicit block reason + retry metadata.

**Step 3: Verification ladder**

Run and store logs:

```bash
.venv/bin/python -m py_compile $(find src -name '*.py')
.venv/bin/python -m pytest tests/unit/ -x
.venv/bin/python -m pytest --cov-fail-under=80
```

**Step 4: Execute final subagent review loop**

Final pass requires both reviewers `OK` and complete evidence links.

## Done Definition

1. Runtime evidence bundle exists with required files and reviewer approvals.
2. Roadmap F3-4 runtime tasks (`task2/task3`) reflect true runtime status.
3. `DEC-237` policy is applied consistently for pass/blocked outcomes.
4. Verification ladder evidence is stored under `.agents/logs/verification/`.

## Risks and Controls

1. Consumer workload source ambiguity blocks startup.
Control: force explicit architecture decision before rollout attempt.
2. Private AKS network/path instability causes intermittent failures.
Control: jumpbox-only execution path and command-by-command evidence capture.
3. Metrics query access issues hide freshness/lag state.
Control: primary/fallback policy with mandatory `MONITORING_ACCESS_BLOCKED` classification and retry metadata.
