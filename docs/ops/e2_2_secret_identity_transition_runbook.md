# E2-2 Secret and Identity Transition Runbook (dev-first)

## 1) Scope

- Stage: `E2-2` (Cloud-Secure secret/permission transition)
- Environment: `dev` first
- Goal: move from `SAS/env` delivery to `Key Vault + Managed Identity` access path
- Out of scope:
  - Event Hubs resource/auth policy change (external ownership)
  - runtime code change in `src/`
  - direct Azure role assignment execution

## 2) Fixed Policy

- `local`: env values are allowed for fast local development.
- `dev`/`prod`: Key Vault is the source of truth for secrets.
- Secret read path: application identity -> Managed Identity -> Key Vault.
- Event Hubs connection policy is externally owned. We only define dependency contract.

## 3) Secret Catalog (fixed names)

| Secret name | Purpose | Runtime consumer |
| --- | --- | --- |
| `txlookup-database-url` | `DATABASE_URL` value | API, Consumer |
| `txlookup-kafka-sasl-password` | `KAFKA_SASL_PASSWORD` value | Consumer |
| `txlookup-appinsights-connection-string` | `APPLICATIONINSIGHTS_CONNECTION_STRING` value | API, Consumer |

## 4) Transition Procedure

1. Freeze env key inventory for current deployment and map each key to a Key Vault secret name.
2. Confirm Key Vault naming prefix policy (`txlookup-*`) and secret owner.
3. Confirm Managed Identity target principals for API/Consumer workloads.
4. Populate Key Vault secrets and verify access from runtime identity.
5. Validate no plain secret literal remains in deployment env blocks for `dev`.
6. Record evidence under `.agents/logs/verification/<timestamp>_e2_2_secret_rbac_gate/`.

## 5) Rollback Procedure (temporary)

Use only when Key Vault/identity path is blocked and service continuity is at risk.

| Item | Requirement |
| --- | --- |
| Trigger | Key Vault read failure or identity token failure impacting runtime startup |
| Action | Temporary fallback to prior env injection path for affected key only |
| Owner | on-call owner recorded in evidence |
| Approval | service owner + platform owner |
| TTL | max 24 hours (`ttl`) then revert to Key Vault path |
| Exit condition | Key Vault + Managed Identity path verified as healthy |

## 6) Evidence Contract

Required evidence files:

- `01_secret_inventory.log`
- `02_identity_mapping.log`
- `03_keyvault_access_check.log`
- `04_rollback_or_no_rollback.log`
- `99_summary.md`

Every evidence file must include: `command`, `exit_code`, UTC timestamp, owner, result.
