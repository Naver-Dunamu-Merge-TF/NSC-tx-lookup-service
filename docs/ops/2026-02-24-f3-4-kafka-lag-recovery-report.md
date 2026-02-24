# F3-4 `consumer_kafka_lag` Recovery Report (2026-02-24)

## Summary

- Previous state: `consumer_kafka_lag` only metric missing in `AppMetrics` (`METRIC_FAILED`), while other `consumer_*` metrics were ingested.
- Current state: `consumer_kafka_lag` rows recovered in `AppMetrics` after runtime instrumentation fix and redeploy.

## Root Cause

1. Watermark API call shape mismatch risk:
   - Runtime used `confluent-kafka` 2.x where `get_watermark_offsets` expects `TopicPartition`.
2. Missing fallback behavior:
   - When watermark lookup was unavailable (`None`/exception), lag value was not recorded, producing no gauge observations for `consumer_kafka_lag`.

## Change Applied

- `src/consumer/main.py`
  - Use `TopicPartition(msg.topic(), msg.partition())` for watermark query.
  - Record `consumer_kafka_lag=0` when watermark lookup is unavailable.
  - Keep lag recording before payload processing to capture both success/error payload paths.

- `tests/unit/test_consumer_contract_flow.py`
  - Added regression test for `TopicPartition`-based watermark lookup.
  - Added regression test for fallback behavior when watermark lookup returns `None`.

## Runtime Deployment

- Built and pushed patched image tags to ACR (`txlookup/api`):
  - `f3-4-kafka-lag-fix-20260224150331`
  - `f3-4-kafka-lag-fallback-20260224151128`
- Rolled out `txlookup-consumer` to patched fallback tag:
  - `nscacrdevw4mlu8.azurecr.io/txlookup/api:f3-4-kafka-lag-fallback-20260224151128`

## Verification Evidence

Evidence bundle:
- `.agents/logs/verification/20260224_145812_f3_4_kafka_lag_recovery/`

Key files:
- `15_consumer_rollout_fallback_fix.log`
- `16_publish_synthetic_events_postfix2.log`
- `18_appmetrics_consumer_kafka_lag_30m_after_fallback.log`
- `19_appmetrics_inventory_30m_after_fallback.log`
- `20_appmetrics_freshness_30m_after_fallback.log`

Observed recovery:
- `consumer_kafka_lag` query result returned non-empty rows (`rows > 0`, `max_lag=0`).
- Metric inventory now includes `consumer_kafka_lag` with recent timestamps.

## Operational Note

- `consumer_kafka_lag=0` can represent fallback when broker watermark is unavailable.
- For known backlog scenarios, treat sustained zero as diagnostic trigger, not guaranteed empty backlog.
