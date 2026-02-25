# Backoffice Data Project Specs (Sync Consumer, Code-Aligned Hybrid)

작성 기준일: 2026-02-25  
기준 브랜치: `dev` (현재 워킹트리 코드)

> 이 문서는 OLTP 이벤트를 Backoffice DB로 동기화하는 Consumer 계약의 SSOT다.
>
> 연계 문서
> - 상위 정책: `.specs/backoffice_project_specs.md`
> - API/DB 상세: `.specs/backoffice_db_admin_api.md`

---

## 0) 문서 운영 원칙 (Hybrid)

1. **As-Is (코드 구현)**: 현재 코드로 즉시 검증 가능한 동작
2. **Target (To-Be)**: 향후 도입/승격 목표
3. **Out of Scope / Reserved**: 현재 범위 밖 또는 예약 기능

---

## 1) 범위 및 책임 경계

### As-Is (코드 구현)

- 이벤트 소비: Kafka/Event Hubs 토픽 consume
- 정규화/검증: topic profile + alias/core_required 정책
- DB 반영: 멱등 upsert(`ledger_entries`, `payment_orders`, `payment_ledger_pairs`)
- 운영 기능: DLQ 저장(file/db), backfill(JSONL), freshness/lag/계약지표 관측

### Target (To-Be)

- 보안형 Cloud-Secure 운영 승격(E2) 및 운영 자동화(E3) 강화

### Out of Scope / Reserved

- producer(이벤트 발행) 구현
- 카프카/모니터링 인프라 프로비저닝
- 결제 원천 도메인 상태전이 로직

---

## 2) 이벤트 계약: profile 기반 topic 매핑

## 2.1 프로파일/토픽 선택 규칙

### As-Is (코드 구현)

환경변수
- `EVENT_PROFILE_ID` (기본: `canonical-v1`)
- `LEDGER_TOPIC`, `PAYMENT_ORDER_TOPIC` (선택 override)

우선순위
- 키별 `env override > profile topics > default`
- 두 effective topic이 동일하면 프로세스 시작 시 fail-fast

기본 프로파일 매핑

| profile_id | ledger topic | payment_order topic |
|---|---|---|
| `canonical-v1` | `ledger.entry.upserted` | `payment.order.upserted` |
| `nsc-dev-v1` | `cdc-events` | `order-events` |

소스: `configs/event_profiles.yaml`

## 2.2 alias / core_required

### As-Is (코드 구현)

Alias

| canonical | alias |
|---|---|
| `entry_type` | `type` |
| `event_time` | `source_created_at`, `created_at` |
| `version` | `source_version` |

Core required

- ledger: `tx_id`, `wallet_id`, `entry_type`, `amount`, `event_time_or_alias`
- payment_order: `order_id`, `amount`, `status`, `created_at`

정규화 규칙
- alias 후보 중 non-empty 첫 값을 채택
- alias 그룹에서 상이한 non-empty 값 충돌 시 `contract_core_violation`
- core required 누락 시 parse 계열 오류로 처리

### Target (To-Be)

- profile별 별도 성숙도 임계치 운영 자동화

### Out of Scope / Reserved

- 런타임 hot-reload 기반 프로파일 교체

---

## 3) 이벤트 모델 파싱 규칙

### As-Is (코드 구현)

### 3.1 Ledger (`LedgerEntryUpserted`)

- 필수: `tx_id`, `wallet_id`, `entry_type(or type)`, `amount`, `event_time(or alias)`
- 시간 필드
  - `event_time = event_time || source_created_at || created_at`
  - `created_at = source_created_at || created_at || event_time`
- 버전 필드
  - `source_version = version || source_version`
  - `updated_at`는 optional
- `amount_signed` 미제공 시 `NULL`

### 3.2 Payment Order (`PaymentOrderUpserted`)

- 필수: `order_id`, `amount`, `status`, `created_at`
- `updated_at`/`source_version` optional

### Target (To-Be)

- 이벤트 스키마 버전별 강제 검증 레이어 추가

### Out of Scope / Reserved

- 삭제(tombstone) 이벤트 처리

---

## 4) Consumer 처리 파이프라인

### As-Is (코드 구현)

처리 순서(consume/backfill 공통 핵심)

1. topic 수신 및 payload(JSON object) 파싱
2. correlation id 추출(headers 우선, payload fallback)
3. `normalize_payload_for_topic()`으로 alias 정규화 + core_required 검증
4. topic kind별 이벤트 객체 파싱(`LedgerEntryUpserted` 또는 `PaymentOrderUpserted`)
5. DB upsert 실행 + pairing 업데이트(조건부)
6. 메트릭 기록(`messages`, `lag`, `freshness`, `version_missing`, `contract_*`)
7. 결과 반영
   - consume 경로: 성공 시 commit, 실패 시 DLQ 기록 후 commit(포이즌 메시지 무한 재시도 방지)
   - backfill 경로: Kafka offset commit 없음(JSONL 입력 단위 처리)

오류 분류 코드
- `contract_core_violation`
- `unsupported_topic`
- `parse_error`
- `internal_error`

### Target (To-Be)

- 장애 유형별 재처리 우선순위 자동 분류

### Out of Scope / Reserved

- Exactly-once 전송 보장

---

## 5) 멱등성 / LWW 정책

### As-Is (코드 구현)

Upsert 키
- `ledger_entries`: `tx_id`
- `payment_orders`: `order_id`
- `payment_ledger_pairs`: `payment_order_id`

LWW 우선순위
1. `incoming.updated_at`가 있으면 `existing.updated_at`과 비교해 최신값 반영
2. `incoming.updated_at`가 없고 `incoming.source_version`이 있으면 version 비교
3. 둘 다 없을 때만 `ingested_at` 비교 fallback
   - 단, fallback은 **incoming/existing 모두 metadata(`updated_at`, `source_version`) 부재**일 때만 허용

효과
- metadata 있는 기존 레코드를 metadata 없는 이벤트가 덮어쓰지 못한다.

메타데이터 누락 관측
- `updated_at`와 `source_version` 둘 다 없으면 `consumer_version_missing_total` 증가

### Target (To-Be)

- 업스트림 메타데이터 제공률 SLA 강화

### Out of Scope / Reserved

- 비관적 락 기반 순서 보장 처리

---

## 6) Pairing 정책

### As-Is (코드 구현)

트리거 조건
- ledger 이벤트에서 `related_id`가 있고 `related_type in {None, PAYMENT_ORDER}`일 때만 pairing 계산
- 그 외 `related_type`은 pairing 스킵(`pairing_skipped_non_payment_order_total`)

계산 규칙
- 같은 `related_id` 그룹에서 `PAYMENT`와 `RECEIVE`를 찾아 pair snapshot 계산
- complete: PAYMENT/RECEIVE 모두 존재
- incomplete: 한쪽만 존재

회귀 방지
- 기존 pair가 complete면 새로운 incomplete 결과로 downgrade하지 않는다.

저장소
- `bo.payment_ledger_pairs` upsert

### Target (To-Be)

- reversal/refund 타입 포함 다중 pair 정책 확장

### Out of Scope / Reserved

- `related_type` 전 도메인 공통 pairing 단일화

---

## 7) DLQ / 재처리 정책

### As-Is (코드 구현)

DLQ 백엔드
- `DLQ_BACKEND=file` (기본: local/dev)
- `DLQ_BACKEND=db` (기본: prod)

저장 대상
- topic/partition/offset/key/payload/error/correlation_id/ingested_at

보관
- DB backend 사용 시 `DLQ_RETENTION_DAYS` 기준 prune 수행

재처리
- 실시간 consume 외에 `backfill` 명령(JSONL 입력)으로 재적재 가능
- `--since/--until`로 시간 범위 제한 가능

### Target (To-Be)

- 운영형 DLQ replay 자동화 및 승인 게이트 통합

### Out of Scope / Reserved

- DLQ 전용 별도 큐 인프라 내장

---

## 8) 관측성 계약

### As-Is (코드 구현)

Consumer 핵심 지표
- 처리량/결과: `consumer_messages_total`
- 지연: `consumer_event_lag_seconds`, `consumer_kafka_lag`
- 신선도: `consumer_freshness_seconds`
- 실패: `consumer_dlq_total`
- 계약 성숙도: `consumer_contract_alias_hit_total`, `consumer_contract_core_violation_total`, `consumer_contract_profile_messages_total`
- 메타데이터 누락: `consumer_version_missing_total`
- 페어링 품질: `pairing_total`, `pairing_incomplete_total`, `pairing_incomplete_age_seconds`, `pairing_skipped_non_payment_order_total`

Freshness 기준 시각
- ledger: `event_time`
- payment_order: `updated_at || created_at`

### Target (To-Be)

- 운영 대시보드/알림 튜닝 자동화

### Out of Scope / Reserved

- 장기 시계열 분석 파이프라인 자체 구축

---

## 9) 운영 단계 정렬 (프로젝트 스펙과 동일 용어)

### As-Is (코드 구현)

- F축: F1/F2 기능 구현 완료, F3 품질/운영 게이트 진행
- E축: E1 검증 이력 존재, E2 진행, E3 예정

> 단계별 상세 상태/증빙은 `.roadmap/implementation_roadmap.md`를 따른다.

### Target (To-Be)

- E2 완료 후 Cloud-Secure 운영 표준 고정, E3 자동화 완성

### Out of Scope / Reserved

- 단계별 상세 일정 관리

---

## 10) Reserved Topic 명시

### As-Is (코드 구현)

- `PaymentLedgerPaired` 토픽은 현재 consumer에서 직접 consume하지 않는다.
- 현재 pair 테이블은 ledger/payment_order 이벤트 기반 계산으로 채운다.

### Target (To-Be)

- 업스트림에서 `PaymentLedgerPaired`를 안정적으로 제공하면 보조 입력으로 도입 검토

### Out of Scope / Reserved

- 현 단계에서 `PaymentLedgerPaired` 기반 단일 진실 경로 전환

---

## 11) Open Issues (실제 미결)

1. `related_type` 다중 도메인 확장 시 pair 저장 모델 분리 여부
2. reversal/refund 이벤트를 포함한 pairing 일반화 규칙
3. `PaymentLedgerPaired` 도입 시 기존 계산 경로와의 충돌/우선순위 정책
