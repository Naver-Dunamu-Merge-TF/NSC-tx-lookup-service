# Integration Topic Checklist

> **이벤트 계약**: 이 체크리스트는 업스트림 프로듀서 팀(CryptoSvc, AccountSvc, CommerceSvc)이
> 발행해야 하는 이벤트 계약이다. tx-lookup-service는 컨슈머로서 이 계약에 따라 이벤트를 수신한다.
> (DEC-112 참조)

## Required topics

1) Ledger entry upsert topic (default: `ledger.entry.upserted`)
Required fields
- `tx_id`
- `wallet_id`
- `entry_type`
- `amount`
- `related_id` (recommended)
- `event_time` or `source_created_at`
- `updated_at` or `version`

Optional fields
- `amount_signed`
- `related_type`
- `schema_version`
- `occurred_at`

Sample message
```json
{"tx_id":"tx-001","wallet_id":"wallet-001","entry_type":"PAYMENT","amount":"10000.00","amount_signed":"-10000.00","related_id":"po-001","related_type":"PAYMENT_ORDER","event_time":"2026-02-05T01:00:00Z","updated_at":"2026-02-05T01:00:01Z","version":1}
```

2) Payment order upsert topic (default: `payment.order.upserted`)
Required fields
- `order_id`
- `amount`
- `status`
- `created_at`
- `updated_at` or `version`

Optional fields
- `user_id`
- `merchant_name`
- `schema_version`
- `occurred_at`

Sample message
```json
{"order_id":"po-001","user_id":"user-001","merchant_name":"MERCHANT-001","amount":"10000.00","status":"SETTLED","created_at":"2026-02-05T01:00:00Z","updated_at":"2026-02-05T01:00:01Z","version":1}
```

## Optional topic

3) Payment ledger paired topic (if service emits)
Required fields
- `payment_order_id`
- `payment_tx_id`
- `receive_tx_id`
- `payer_wallet_id`
- `payee_wallet_id`
- `amount`
- `updated_at`
