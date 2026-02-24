# F3-4 Infra Preaction Report (2026-02-24)

## Scope

- Objective: unblock AKS pod -> Application Insights telemetry path for F3-4 runtime closeout.
- Mode: diagnose first, apply minimal preaction, verify, then report to infra team.
- Resource group: `2dt-final-team4`
- Firewall policy: `nsc-fwp-dev`
- Rule collection group: `nsc-rcg-default`
- Rule collection: `allow-fqdn`

## Diagnosis Summary

- Azure Firewall diagnostics showed repeated denies with `No rule matched` for telemetry domains:
  - `dc.services.visualstudio.com:443`
  - `koreacentral-0.in.applicationinsights.azure.com:443`
  - `koreacentral.livediagnostics.monitor.azure.com:443`
- Source IPs matched AKS application subnet (`10.0.2.x`).
- This matched runtime symptom (`UNEXPECTED_EOF_WHILE_READING`) from consumer exporter.

## Preaction Applied

- Added Firewall application rule:
  - name: `allow-appinsights-telemetry`
  - source: `10.0.2.0/23`
  - protocol: `Https=443`
  - target FQDNs:
    - `dc.services.visualstudio.com`
    - `*.in.applicationinsights.azure.com`
    - `*.livediagnostics.monitor.azure.com`

## Post-Change Verification

- Firewall logs switched from deny to allow for telemetry domains using the new rule.
- Consumer pod checks:
  - DNS resolve: OK
  - TCP 443 connect: OK
  - TLS handshake: OK (`TLSv1.3`) for `in.applicationinsights` and `dc.services.visualstudio.com`
- AppMetrics resumed ingestion for consumer metrics:
  - `consumer_freshness_seconds`
  - `consumer_messages_total`
  - `consumer_event_lag_seconds`

## Residual Issue

- `consumer_kafka_lag` is still not observed in `AppMetrics` (P1D and closeout windows).
- Since network path is now verified, this is classified as application instrumentation issue (`METRIC_FAILED`), not infra egress block.

## Infra Team Follow-up Requested

- Keep the preaction rule in effect until IaC formalization is complete.
- Port the exact rule (`allow-appinsights-telemetry`) into Terraform/official firewall policy definition.
- Confirm no conflicting downstream policy overrides this rule.

## Evidence Bundle

- `.agents/logs/verification/20260224_143303_f3_4_infra_preaction/`
- Key files:
  - `06_firewall_appinsights_denies.log`
  - `09_firewall_preaction_add_rule.log`
  - `13_postchange_firewall_actions_5m_detail.log`
  - `14_postchange_consumer_tls_checks_retry.log`
  - `17_postchange_appmetrics_raw_30m.log`
  - `21_postchange_consumer_metric_inventory.log`
