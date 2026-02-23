# F3-2 SLO Alert Rules Operational Runbook (Dev)

## 1) Scope

- Environment: `dev` only (`2dt-final-team4`)
- Objective: apply `docker/observability/alert_rules.yml` into Azure Monitor Scheduled Query Rules and collect operation evidence
- Out of scope: IaC(Bicep/Terraform), Cloud-Secure(E2) rollout

## 2) Fixed Inputs

Set these variables before running checks:

- `SUBSCRIPTION_ID=27db5ec6-d206-4028-b5e1-6004dca5eeef`
- `RESOURCE_GROUP=2dt-final-team4`
- `APP_INSIGHTS_ID=/subscriptions/<sub>/resourceGroups/2dt-final-team4/providers/microsoft.insights/components/nsc-ai-dev`
- `LAW_WORKSPACE_ID=/subscriptions/<sub>/resourceGroups/2dt-final-team4/providers/Microsoft.OperationalInsights/workspaces/nsc-law-dev`
- `ACTION_GROUP_ID=/subscriptions/<sub>/resourceGroups/2dt-final-team4/providers/microsoft.insights/actionGroups/<platform-team-managed-name>`

Action Group receivers(email/Teams/webhook) are managed by platform team. This repository stores interface only (`ACTION_GROUP_ID`).

## 3) Rule Mapping (Source of Truth)

Azure rule names are fixed to the same names as `docker/observability/alert_rules.yml`.

| Rule | Metric | Severity | Window |
| --- | --- | --- | --- |
| `ApiLatencyHigh` | `api_request_latency_seconds` | `warning` | `5m` |
| `ApiErrorRateHigh` | `api_requests_total` | `warning` | `5m` |
| `DataFreshnessHigh` | `consumer_freshness_seconds` | `critical` | `5m` |
| `DlqActivity` | `consumer_dlq_total` | `warning` | `5m` |
| `ContractCoreViolationHigh` | `consumer_contract_core_violation_total` | `warning` | `5m` |
| `DbPoolExhausted` | `db_pool_checked_out` | `warning` | `5m` |
| `DbPoolCheckoutSlow` | `db_pool_checkout_latency_seconds` | `warning` | `5m` |
| `DbReplicationLagHigh` | `db_replication_lag_seconds` | `critical` | `5m` |

Severity policy (DEC-202) is fixed:

- `critical`: `DataFreshnessHigh`, `DbReplicationLagHigh`
- `warning`: all other rules

## 4) Azure Query Baseline

For workspace-based Application Insights, use `AppMetrics` table and schema:

- `Name`
- `Sum`
- `Max`
- `ItemCount`
- `Properties`
- `TimeGenerated`

Do not use `customMetrics` as F3-2 baseline.

## 5) Apply Procedure (Portal + CLI evidence)

1. Pre-check existing resources:
   - `az resource list -g $RESOURCE_GROUP --resource-type microsoft.insights/scheduledqueryrules`
   - `az resource list -g $RESOURCE_GROUP --resource-type microsoft.insights/actiongroups`
2. Create/confirm Action Group from platform input and resolve `ACTION_GROUP_ID`.
3. In Azure Portal, create 8 Scheduled Query Rules using KQL snippets from `docker/observability/alert_rules.yml` (already converted to `AppMetrics`).
4. For every rule, set:
   - Scope: `nsc-ai-dev` / `nsc-law-dev` workspace context
   - Evaluation frequency: `5m`
   - Aggregation window: `5m`
   - Action Group: `$ACTION_GROUP_ID`
   - Enabled: `true` (immediate activation)
5. Post-check:
   - `az resource list -g $RESOURCE_GROUP --resource-type microsoft.insights/scheduledqueryrules`
   - `az resource show --ids <scheduled-query-rule-id>`

## 6) Dashboard Link Evidence (KQL + Logs)

Store KQL outputs as evidence logs under:
`.agents/logs/verification/<timestamp>_f3_2_slo_alert_ops/`

### 6.1 API latency (`03_dashboard_api_latency.log`)

```kql
AppMetrics
| where Name == "api_request_latency_seconds"
| summarize p95 = percentile(Sum, 95) by bin(TimeGenerated, 5m)
| order by TimeGenerated desc
```

### 6.2 Consumer freshness (`04_dashboard_consumer_freshness.log`)

```kql
AppMetrics
| where Name == "consumer_freshness_seconds"
| summarize max_freshness = max(Max) by bin(TimeGenerated, 5m)
| order by TimeGenerated desc
```

### 6.3 DB pool group (`05_dashboard_db_pool.log`)

Required metrics:

- `db_pool_size`
- `db_pool_checked_out`
- `db_pool_overflow`
- `db_pool_checked_in`
- `db_pool_checkout_latency_seconds`

```kql
AppMetrics
| where Name in (
    "db_pool_size",
    "db_pool_checked_out",
    "db_pool_overflow",
    "db_pool_checked_in",
    "db_pool_checkout_latency_seconds"
)
| summarize latest = max(TimeGenerated), max_value = max(Max) by Name
| order by Name asc
```

### 6.4 DB replication lag (`06_dashboard_db_replication.log`)

```kql
AppMetrics
| where Name == "db_replication_lag_seconds"
| summarize max_lag = max(Max) by bin(TimeGenerated, 5m)
| order by TimeGenerated desc
```

## 7) Alert Drill (Trigger -> Remediate -> Recover)

Fixed drill scenarios:

1. Warning drill: `DlqActivity`
   - Inject malformed event (`scripts/publish_synthetic_events.py --scenario error --run-id f3-2-dlq-drill`)
2. Critical drill: `DataFreshnessHigh`
   - Inject stale `event_time` payload and verify freshness breach

For each drill, record:

- 발생 시각 (Detected at)
- 조치 시각 (Mitigation started)
- 복구 시각 (Recovered at)
- 근거 KQL (query + result summary)

Template:

```text
rule=<RULE_NAME>
detected_at=<UTC_ISO8601>
mitigation_started_at=<UTC_ISO8601>
recovered_at=<UTC_ISO8601>
evidence_kql=<saved query name>
evidence_log=<verification log file>
```

## 8) 3-Day Tuning Loop

Baseline: keep DEC-202 thresholds/severity for first 3 days.

- False positive candidate: same rule has non-actionable violations `>=3/day`
- Missed detection: drill event did not trigger expected rule

If tuning is required:

1. Update `docker/observability/alert_rules.yml`
2. Update `.specs/decision_open_items.md` (related DEC entry)
3. Update this runbook (`docs/ops/f3_2_slo_alerts_runbook.md`)
4. Re-run targeted tests and store logs

## 9) Evidence Bundle Layout

Required files:

- `01_l0_py_compile.log`
- `02_l1_targeted.log`
- `03_dashboard_api_latency.log`
- `04_dashboard_consumer_freshness.log`
- `05_dashboard_db_pool.log`
- `06_dashboard_db_replication.log`
- `07_warning_drill.log`
- `08_critical_drill.log`
- `09_azure_resource_state.log`
- `99_f3_2_completion_summary.md`
