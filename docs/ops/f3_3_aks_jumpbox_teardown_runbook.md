# F3-3 AKS Jumpbox Teardown Runbook

## Scope

Mandatory same-day cleanup for jumpbox resources used in F3-3 validation.

Target names for 2026-02-24 run:

- VM: `jump-aks-20260224-2dt026`
- NIC: `nic-jump-aks-20260224-2dt026`
- OS disk: `osdisk-jump-aks-20260224-2dt026`
- Optional data disk: `datadisk-jump-aks-20260224-2dt026-01`

## Deletion order (mandatory)

1. VM delete
2. NIC delete
3. OS disk delete
4. Optional data disk delete
5. Optional public IP delete (if created unexpectedly)
6. Residual resource scan by tag

## Execution gate (mandatory)

- Teardown commands must run only after **explicit requester instruction**.
- If explicit instruction is not yet given, do not run delete commands.
- Record `teardown_pending=true` in pilot summary evidence and keep resource inventory snapshot output in the same evidence bundle.
- Once explicit instruction is given, execute the full teardown in the same day (same-day cleanup SLA).

## Command sequence

```bash
az vm delete --resource-group 2dt-final-team4 --name jump-aks-20260224-2dt026 --yes
az vm wait --resource-group 2dt-final-team4 --name jump-aks-20260224-2dt026 --deleted --interval 10 --timeout 600
az network nic delete --resource-group 2dt-final-team4 --name nic-jump-aks-20260224-2dt026
az disk delete --resource-group 2dt-final-team4 --name osdisk-jump-aks-20260224-2dt026 --yes
az disk delete --resource-group 2dt-final-team4 --name datadisk-jump-aks-20260224-2dt026-01 --yes
```

Use `az disk delete --yes` for each managed disk target.

Optional PIP cleanup:

```bash
az network public-ip list --resource-group 2dt-final-team4 --query \"[?tags.purpose=='f3-3-jumpbox'].name\" -o tsv
az network public-ip delete --resource-group 2dt-final-team4 --name <pip-name>
```

Residual scan:

```bash
az resource list --tag purpose=f3-3-jumpbox --query '[].{name:name,type:type,resourceGroup:resourceGroup}' -o table
az resource list --tag purpose=f3-3-jumpbox --query 'length(@)' -o tsv
```

Expected final state: zero resources (`residual_count=0`).

## Failure handling (conflict/lock)

If deletion returns conflict or lock errors:

1. Re-run `az vm wait --deleted` for VM state convergence.
2. Retry dependent deletes (NIC/disk) after VM delete is confirmed.
3. If resource lock blocks deletion, collect `az lock list --resource-group 2dt-final-team4` output and escalate to platform owner.
4. Keep evidence bundle as `blocked` until residual count reaches zero.

Idempotency rule:

- Re-running teardown is allowed.
- If delete commands return `NotFound`, treat that target as already cleaned and continue.

## Evidence requirements

Store logs under `.agents/logs/verification/`.

Suggested directory:

`.agents/logs/verification/<timestamp>_f3_3_jumpbox_pilot/`

Every command log must include:

- `command`
- `exit_code`
- `UTC timestamp`

Add a final summary record named `teardown_evidence_summary` with at least:

- `result=pass|blocked`
- `residual_count=0`
- `owner=<responsible owner>`
