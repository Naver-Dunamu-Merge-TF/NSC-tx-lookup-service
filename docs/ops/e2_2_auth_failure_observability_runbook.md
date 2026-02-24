# E2-2 Auth Failure Observability and Audit Split Runbook

## 1) Scope

This runbook defines split tracing for:

- auth failure path: `401`, `403`
- lookup/audit path: `200`, `404` records in `bo.admin_audit_logs`

## 2) Split Contract

- `401`/`403`: captured at auth layer before route logic; tracked in App/Gateway/AppInsights logs.
- `200`/`404`: route execution path; tracked in DB audit table `bo.admin_audit_logs`.
- No policy change: auth failure path remains outside DB audit insert scope.

## 3) Required Queries

### 3.1 AppInsights / Gateway side (`401`/`403`)

```kql
AppRequests
| where Url has "/admin/"
| where ResultCode in ("401", "403")
| summarize count() by ResultCode, bin(TimeGenerated, 5m)
| order by TimeGenerated desc
```

If `AppRequests` is unavailable, use gateway/access log query with equivalent filter on `/admin/*` and status in `401/403`.

### 3.2 PostgreSQL audit side (`200`/`404`)

```sql
SELECT
  status_code,
  COUNT(*) AS row_count,
  COALESCE(SUM(result_count), 0) AS total_result_count
FROM bo.admin_audit_logs
WHERE requested_at >= NOW() - INTERVAL '1 day'
  AND status_code in (200,404)
GROUP BY status_code
ORDER BY status_code;
```

## 4) Minimum Evidence

Store outputs under `.agents/logs/verification/<timestamp>_e2_2_secret_rbac_gate/`:

- `05_auth_failures_401_403.log`
- `06_admin_audit_200_404.log`
- `07_split_validation_summary.md`

## 5) Failure Handling

- Missing 401/403 log rows with known denied requests: classify as observability pipeline issue.
- Missing DB audit rows for 200/404: classify as application audit path issue.
- Record owner, retry date, and unblock criteria in summary.
