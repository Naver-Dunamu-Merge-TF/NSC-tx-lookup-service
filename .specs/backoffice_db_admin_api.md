# Backoffice DB + Admin API Specs (Code-Aligned Hybrid)

작성 기준일: 2026-02-25  
기준 브랜치: `dev` (현재 워킹트리 코드)

> 이 문서는 Admin API + Serving DB 계약의 SSOT다.
>
> 연계 문서
> - 상위 정책: `.specs/backoffice_project_specs.md`
> - 동기화/이벤트: `.specs/backoffice_data_project.md`

---

## 0) 문서 운영 원칙 (Hybrid)

1. **As-Is (코드 구현)**: `src/api/*`, `src/db/*`, `migrations/*` 기준 현재 동작
2. **Target (To-Be)**: 미구현이지만 향후 도입할 목표
3. **Out of Scope / Reserved**: 현재 범위 밖 또는 예약 항목

---

## 1) 도메인 용어 사전

### As-Is (코드 구현)

- `tx_id`: `bo.ledger_entries` PK, 원장 엔트리(행) ID
- `related_id`: 페어링 조인 키(일반적으로 `payment_orders.order_id`)
- `pairing_status`: `COMPLETE | INCOMPLETE | UNKNOWN`
- `status_group`: `SUCCESS | FAIL | IN_PROGRESS | UNKNOWN`
- `source_version`: 이벤트 버전 메타데이터
- `ingested_at`: Backoffice DB에 반영된 시각

### Target (To-Be)

- 환불/정정 도메인 확장 시 `related_type`별 용어 집합을 분리할 수 있다.

### Out of Scope / Reserved

- 결제 도메인 원천 상태 머신(업스트림 내부 상태전이) 정의

---

## 2) Admin API 계약

## 2.1 엔드포인트 목록

### As-Is (코드 구현)

1. `GET /admin/tx/{tx_id}`
2. `GET /admin/payment-orders/{order_id}`
3. `GET /admin/wallets/{wallet_id}/tx`

모든 엔드포인트는 인증/인가 의존성(`require_admin_read`)을 거친다.

### Target (To-Be)

- 필요 시 페이지네이션/정렬 옵션 확장

### Out of Scope / Reserved

- 배치 조회 POST API

---

## 2.2 `GET /admin/tx/{tx_id}`

### As-Is (코드 구현)

상태 코드
- `200`: 조회 성공
- `404`: `tx_id` 미존재
- `401`: 인증 실패(JWT 누락/검증 실패)
- `403`: 역할 부족

조회 조립 순서
1. `LedgerEntry`를 `tx_id`로 조회
2. `PaymentOrder`, `PaymentLedgerPair`를 `related_id` 기준 outer join
3. pair가 없거나 incomplete면, 같은 `related_id`에서 **반대 entry_type** peer를 fallback 조회

응답 필드
- `tx_id`, `event_time`, `entry_type`, `amount`, `amount_signed`
- `status`(payment order 원문), `status_group`
- `sender_wallet_id`, `receiver_wallet_id`
- `related.related_id`, `related.related_type`
- `paired_tx_id`, `merchant_name`
- `pairing_status`, `data_lag_sec`

응답 정책
- `related_id` 없거나 `related_type != PAYMENT_ORDER`면 `pairing_status=UNKNOWN`
- `PAYMENT`/`RECEIVE` 양쪽 tx가 있으면 `COMPLETE`, 아니면 `INCOMPLETE`
- `data_lag_sec = now - max(ingested_at, event_time)` (초 단위, 음수 방지)

### Target (To-Be)

- 상태 원인 코드(error reason) 등 운영 보조 필드 확장 가능

### Out of Scope / Reserved

- 거래 원장 원문 payload 전체 반환

---

## 2.3 `GET /admin/payment-orders/{order_id}`

### As-Is (코드 구현)

상태 코드
- `200`: 조회 성공
- `404`: `order_id` 미존재
- `401/403`: 인증/인가 실패

동작
- `PaymentOrder`를 `order_id`로 조회
- `LedgerEntry`를 `related_id=order_id`로 조회(`event_time DESC, tx_id` 정렬)
- `PaymentLedgerPair`를 `payment_order_id=order_id`로 조회

응답
- `order`: 주문 상세(`order_id`, `user_id`, `merchant_name`, `amount`, `status`, `status_group`, `created_at`)
- `ledger_entries`: 엔트리 목록
- `pairing_status`:
  - pair complete면 `COMPLETE`
  - pair 미완성 + 엔트리 존재면 `INCOMPLETE`
  - 엔트리도 없으면 `UNKNOWN`

### Target (To-Be)

- 기간/상태 필터 지원

### Out of Scope / Reserved

- 주문 변경 이력 타임라인 API

---

## 2.4 `GET /admin/wallets/{wallet_id}/tx`

### As-Is (코드 구현)

상태 코드
- `200`: 조회 성공(빈 목록 포함)
- `401/403`: 인증/인가 실패

쿼리 파라미터
- `from` (optional, ISO-8601)
- `to` (optional, ISO-8601)
- `limit` (default `20`, range `1..100`)

동작
- `wallet_id` 기준 `LedgerEntry` 조회
- `from/to`가 있으면 `event_time` 범위 필터 적용
- `event_time DESC, tx_id` 정렬 후 `limit`

응답
- `wallet_id`
- `entries[]` (`LedgerEntryItem`)
- `count`

### Target (To-Be)

- cursor 기반 페이지네이션

### Out of Scope / Reserved

- 지갑 잔액 계산 API

---

## 3) 응답 계산 규칙

## 3.1 `related_type` 해석

### As-Is (코드 구현)

1. ledger의 `related_type`가 있으면 그대로 사용
2. 없고 payment order join이 성공하면 `PAYMENT_ORDER`
3. 둘 다 아니면 `UNKNOWN`

---

## 3.2 `pairing_status` / `paired_tx_id` 계산

### As-Is (코드 구현)

- 입력 소스 우선순위
1. `payment_ledger_pairs`
2. peer fallback(`related_id` + 반대 `entry_type`)
3. 현재 ledger row

- 판단
- `payment_tx_id`와 `receive_tx_id`가 모두 있으면 `COMPLETE`
- 하나라도 없으면 `INCOMPLETE`
- payment order 문맥이 아니면 `UNKNOWN`

- `paired_tx_id`
- 현재 row가 `PAYMENT`면 `receive_tx_id`
- 현재 row가 `RECEIVE`면 `payment_tx_id`

---

## 3.3 `status_group` 매핑(v1)

### As-Is (코드 구현)

- `SUCCESS`: `SETTLED`, `COMPLETED`, `SUCCESS`, `SUCCEEDED`, `PAID`
- `FAIL`: `FAILED`, `CANCELLED`, `CANCELED`, `REJECTED`, `DECLINED`
- `IN_PROGRESS`: `CREATED`, `PENDING`, `PROCESSING`, `AUTHORIZED`
- 그 외/NULL: `UNKNOWN`

원문 `status`는 그대로 보존해 응답한다.

---

## 4) 인증/인가/감사

### As-Is (코드 구현)

인증 모드
- `AUTH_MODE=disabled`: 개발용 헤더(`X-Actor-Id`, `X-Actor-Roles`) 사용
- `AUTH_MODE=oidc`: Bearer JWT 검증(`issuer`, `audience`, `jwks`)

역할
- `ADMIN_READ` 또는 `ADMIN_AUDIT` 중 하나 보유 시 허용

감사로그 저장
- 테이블: `bo.admin_audit_logs`
- 저장 필드: `actor_id`, `actor_roles`, `action`, `resource_*`, `result`, `status_code`, `request_*`, `duration_ms`, `result_count`, `requested_at`

주의
- `401/403`은 라우트 진입 전 차단될 수 있으므로 DB 감사로그 대신 인증 계층 로그에서 추적한다.

### Target (To-Be)

- 운영형 환경에서 `AUTH_MODE=disabled` 완전 제거

### Out of Scope / Reserved

- IdP 조직 정책(tenant-level security baseline) 관리

---

## 5) Serving DB 스키마

## 5.1 핵심 조회 테이블

### As-Is (코드 구현)

1. `bo.ledger_entries`
- PK: `tx_id`
- 주요 컬럼: `wallet_id`, `entry_type`, `amount`, `amount_signed`, `related_id`, `related_type`, `event_time`, `created_at`, `updated_at`, `source_version`, `ingested_at`
- 인덱스: `related_id`, `(wallet_id, event_time)`, `event_time`

2. `bo.payment_orders`
- PK: `order_id`
- 주요 컬럼: `user_id`, `merchant_name`, `amount`, `status`, `created_at`, `updated_at`, `source_version`, `ingested_at`
- 인덱스: `user_id`, `merchant_name`, `status`, `created_at`

3. `bo.payment_ledger_pairs`
- PK: `payment_order_id`
- 주요 컬럼: `payment_tx_id`, `receive_tx_id`, `payer_wallet_id`, `payee_wallet_id`, `amount`, `status`, `event_time`, `updated_at`, `ingested_at`
- 인덱스: `payment_tx_id`, `receive_tx_id`

## 5.2 운영 테이블

### As-Is (코드 구현)

4. `bo.admin_audit_logs`
- Identity PK: `audit_id`
- 감사 필드 + `result_count`

5. `bo.consumer_dlq_events`
- Identity PK: `dlq_id`
- DLQ triage 필드(`topic`, `partition`, `offset`, `key`, `payload`, `error`, `correlation_id`, `ingested_at`)

### Target (To-Be)

- 운영 쿼리 패턴 증가 시 materialized view 도입 검토

### Out of Scope / Reserved

- `bo.admin_tx_search` 물리 뷰/테이블은 현재 미구현(옵션)

---

## 6) 쿼리 경로 요약

### As-Is (코드 구현)

- `fetch_admin_tx_context()`
  - `LedgerEntry` 기준으로 `PaymentOrder`, `PaymentLedgerPair` outer join
  - pair 불완전 시 반대 `entry_type` peer fallback 조회

- `fetch_admin_order_context()`
  - order 존재 여부 확인
  - related ledger 목록 + pair row 조회

- `fetch_admin_wallet_tx()`
  - wallet/time-range/limit 기반 목록 조회

### Target (To-Be)

- 조회 빈도/지연 분석 후 특정 경로 캐시 또는 뷰 최적화 검토

### Out of Scope / Reserved

- OLTP 직접 조회 fallback 경로

---

## 7) 테스트 기준 (계약 검증)

### As-Is (코드 구현)

핵심 계약은 아래 테스트로 회귀 검증한다.

- API 라우팅/상태코드/감사: `tests/unit/test_api_routes.py`
- 응답 계산(페어링/status_group): `tests/unit/test_api_service.py`
- DB 조회/감사 영속성: `tests/integration/test_admin_tx_integration.py`
- E2E 흐름: `tests/e2e/test_admin_tx_e2e.py`

### Target (To-Be)

- 운영형 트래픽 패턴 기반 성능 회귀 케이스 추가

### Out of Scope / Reserved

- 장기 보관성/규제 감사 적합성 검증 자체

