# Integration Topic Checklist

> **이벤트 계약**: 이 체크리스트는 업스트림 프로듀서 팀(CryptoSvc, AccountSvc, CommerceSvc)이
> 발행해야 하는 이벤트 계약이다. tx-lookup-service는 컨슈머로서 이 계약에 따라 이벤트를 수신한다.
> (DEC-112 참조)

## 계약 원칙

- **Upsert 전용**: 삭제(tombstone) 이벤트는 지원하지 않는다. 취소/환불은 별도 이벤트로 표현한다 (DEC-224).
- **발행 트리거**: INSERT와 UPDATE 모두. 레코드 상태가 변경될 때마다 최신 스냅샷을 발행한다.
- **멱등성**: Consumer는 at-least-once + 멱등 upsert. 중복 발행해도 결과 동일.
- **순서**: `updated_at` 또는 `version` 기준 latest-wins. 메시지 순서 보장 불필요(권장은 키 기준 파티셔닝).

## Core Required (Compat Core)

Compat Core 모드에서는 아래 필드가 누락되면 DLQ로 격리한다.

1) Ledger (`ledger` logical topic)
- `tx_id`
- `wallet_id`
- `entry_type` (alias: `type`)
- `amount`
- `event_time_or_alias` (`event_time` 또는 alias `source_created_at`, `created_at`)

2) Payment order (`payment_order` logical topic)
- `order_id`
- `amount`
- `status`
- `created_at`

## Profile-specific topic mapping

`EVENT_PROFILE_ID`에 따라 logical topic과 실제 Kafka topic 매핑이 달라진다.

| profile_id | ledger | payment_order |
|-----------|--------|---------------|
| `canonical-v1` | `ledger.entry.upserted` | `payment.order.upserted` |
| `nsc-dev-v1` | `cdc-events` | `order-events` |

우선순위는 키별 `env(LEDGER_TOPIC/PAYMENT_ORDER_TOPIC) > profile > default`다.

## Required topics (profile default: canonical-v1)

1) Ledger entry upsert topic (default: `ledger.entry.upserted`)

Required fields
- `tx_id`
- `wallet_id`
- `entry_type` — 자유 텍스트. 단, 페어링에 사용되는 `PAYMENT`/`RECEIVE`는 반드시 이 값으로 태깅 (DEC-222)
- `amount`
- `related_id` (recommended — 페어링의 조인 키. 없으면 `pairing_status=UNKNOWN`)
- `event_time` or `source_created_at`
- `updated_at` or `version` (강력 권장 — 없으면 ingested_at 기준 fallback, 순서 역전 가능)

Optional fields
- `amount_signed` (없으면 NULL 저장, DEC-204)
- `related_type` (페어링은 `PAYMENT_ORDER`만 지원, DEC-222)
- `schema_version`
- `occurred_at`

Partition key recommendation: `tx_id`

Sample message
```json
{"tx_id":"tx-001","wallet_id":"wallet-001","entry_type":"PAYMENT","amount":"10000.00","amount_signed":"-10000.00","related_id":"po-001","related_type":"PAYMENT_ORDER","event_time":"2026-02-05T01:00:00Z","updated_at":"2026-02-05T01:00:01Z","version":1}
```

2) Payment order upsert topic (default: `payment.order.upserted`)

Required fields
- `order_id`
- `amount`
- `status` — 자유 텍스트. 매핑 안 되는 값은 `status_group=UNKNOWN`으로 그룹핑 (DEC-223)
- `created_at`
- `updated_at` or `version` (강력 권장)

Optional fields
- `user_id`
- `merchant_name`
- `schema_version`
- `occurred_at`

Partition key recommendation: `order_id`

Sample message
```json
{"order_id":"po-001","user_id":"user-001","merchant_name":"MERCHANT-001","amount":"10000.00","status":"SETTLED","created_at":"2026-02-05T01:00:00Z","updated_at":"2026-02-05T01:00:01Z","version":1}
```

취소/환불 처리 예시:
```json
{"order_id":"po-001","user_id":"user-001","merchant_name":"MERCHANT-001","amount":"10000.00","status":"CANCELLED","created_at":"2026-02-05T01:00:00Z","updated_at":"2026-02-05T02:00:00Z","version":2}
```
> 별도 삭제 이벤트 불필요. `status` 업데이트만 보내면 기존 upsert 경로에서 처리됨 (DEC-224).

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

## 필드명 alias 지원

Consumer는 아래 alias를 자동 인식한다. 업스트림 기존 필드명이 다르더라도 아래 중 하나면 파싱 가능:

| 계약 필드명 | 허용 alias |
|-----------|-----------|
| `event_time` | `source_created_at`, `created_at` |
| `entry_type` | `type` |
| `version` | `source_version` |

## status_group 매핑표 (v1, DEC-206)

업스트림 `status` 원문이 아래 값에 해당하면 자동 그룹핑된다 (대소문자 무시):

| status_group | 매핑되는 status 값 |
|-------------|------------------|
| `SUCCESS` | `SETTLED`, `COMPLETED`, `SUCCESS`, `SUCCEEDED`, `PAID` |
| `FAIL` | `FAILED`, `CANCELLED`, `CANCELED`, `REJECTED`, `DECLINED` |
| `IN_PROGRESS` | `CREATED`, `PENDING`, `PROCESSING`, `AUTHORIZED` |
| `UNKNOWN` | 그 외 또는 NULL |

> 매핑에 없는 값도 Consumer 처리에 문제없음. `status` 원문은 항상 보존됨.
> 새 값을 추가하려면 `src/api/service.py`의 `_resolve_status_group()`만 수정.

## F3-1 운영 표준 (2026-02-24)

### `payment_orders.status` 표준 v2 (동결)

- `status`는 업스트림 원문 자유 텍스트를 허용한다.
- `status_group` 계산은 본 문서의 v1 매핑표를 그대로 사용한다(코드: `src/api/service.py`).
- 본 단계(F3-1)에서는 신규 매핑값을 추가하지 않는다.
- 매핑 밖 값은 `status_group=UNKNOWN`으로 그룹핑하고 지표 기반으로 재검토한다(DEC-229, DEC-231).

### `updated_at/version` 제공률 기준 (7일 롤링)

- logical topic별(`ledger`, `payment_order`) `updated_at` 또는 `version` 제공률은 99% 이상이어야 한다(DEC-230).
- 측정 공식:
  - `metadata_coverage_ratio(topic) = 1 - (delta(consumer_version_missing_total{topic}[7d]) / delta(consumer_messages_total{topic,status="success"}[7d]))`
  - 통과 기준: `metadata_coverage_ratio(topic) >= 0.99`

### 계약 성숙도 지표 기준선 (완화 기준)

- `core_violation_rate = delta(consumer_contract_core_violation_total[7d]) / delta(consumer_messages_total{status="success"}[7d]) <= 0.001` (0.1%)
- `alias_hit_ratio = delta(consumer_contract_alias_hit_total[7d]) / delta(consumer_contract_profile_messages_total[7d]) <= 0.40` (40%)
- `version_missing_ratio = delta(consumer_version_missing_total[7d]) / delta(consumer_messages_total{status="success"}[7d]) <= 0.05` (5%)
- 기준선은 profile/topic 단위로 관측하며, 미충족 시 코드 변경보다 계약 보강/재전달을 우선한다(DEC-231).

### 업스트림 전달 이력

- 전달 기록 SSOT: `.specs/upstream_event_contract_handoff_log.md`
