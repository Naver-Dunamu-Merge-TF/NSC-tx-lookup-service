# Local scripts

## Backfill (JSONL)

Use JSON lines dumps and optional time window filtering.

```
python -m src.consumer.main backfill \
  --ledger-file /path/to/ledger.jsonl \
  --payment-order-file /path/to/payment_orders.jsonl \
  --since 2026-02-01T00:00:00Z \
  --until 2026-02-05T00:00:00Z
```

## Publish sample events

```
python scripts/publish_sample_events.py
```

## Replay DLQ file

```
python scripts/replay_dlq.py
```
