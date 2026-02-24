# E2-2 Least Privilege RBAC Matrix (dev)

## 1) Principle

- Baseline: least privilege
- Each principal gets minimum role required for current function only.
- Event Hubs control plane remains external ownership and is change-prohibited in this repository.

## 2) RBAC Matrix

| Resource | Principal | Role | Scope | Owner | Approval | Evidence command |
| --- | --- | --- | --- | --- | --- | --- |
| Key Vault (`nsc-kv-dev`) | API workload identity | Key Vault Secrets User | Key Vault resource scope | tx-lookup service owner | platform security owner | `az role assignment list --scope <kv-scope> --assignee <principal-id>` |
| Key Vault (`nsc-kv-dev`) | Consumer workload identity | Key Vault Secrets User | Key Vault resource scope | tx-lookup service owner | platform security owner | `az role assignment list --scope <kv-scope> --assignee <principal-id>` |
| AKS (`nsc-aks-dev`) | deploy operator group | AKS cluster user (or org-approved read role) | AKS cluster scope | platform team | platform team approver | `az role assignment list --scope <aks-scope> --assignee <principal-or-group>` |
| DB (`nsc-pg-dev`) | API app principal | read-only DB role (`SELECT` only for serving queries) | database schema/table scope | tx-lookup db owner | security reviewer | `psql -c "SELECT grantee, privilege_type FROM information_schema.role_table_grants WHERE table_schema='bo'"` |
| DB (`nsc-pg-dev`) | Consumer app principal | write role for upsert path only | database schema/table scope | tx-lookup db owner | security reviewer | `psql -c "SELECT grantee, privilege_type FROM information_schema.role_table_grants WHERE table_schema='bo'"` |
| DB (`nsc-pg-dev`) | audit reviewer principal | read-only audit access (`bo.admin_audit_logs`) | database schema/table scope | audit owner | security reviewer | `psql -c "SELECT grantee, privilege_type FROM information_schema.role_table_grants WHERE table_name='admin_audit_logs'"` |
| Event Hubs (`nsc-evh-dev`) | tx-lookup service | external ownership (change prohibited) | namespace/hub policy scope | platform messaging team | platform messaging approver | `az eventhubs namespace authorization-rule list -g 2dt-final-team4 --namespace-name nsc-evh-dev` |

## 3) Event Hubs Dependency Contract

- Event Hubs auth/resource policy is external ownership.
- tx-lookup-service does not change namespace network/auth configuration in E2-2.
- Input contract only:
  - connection secret provider owner
  - secret rotation SLA
  - failure escalation channel

## 4) DB Separation Rules

- API principal: lookup/read path only.
- Consumer principal: idempotent upsert write path only.
- Audit access: separate reviewer principal for `bo.admin_audit_logs` review.
