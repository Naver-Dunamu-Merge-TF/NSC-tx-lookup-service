# Backoffice Serving Project Specs (Code-Aligned Hybrid)

작성 기준일: 2026-02-25  
기준 브랜치: `dev` (현재 워킹트리 코드)

> 목적: FR-ADM-02(관리자 거래 추적)를 위해 `tx_id` 중심 조회를 Backoffice Serving Layer에서 안정적으로 제공한다.
>
> 연계 SSOT
> - API/DB 상세: `.specs/backoffice_db_admin_api.md`
> - 동기화/이벤트 상세: `.specs/backoffice_data_project.md`
> - 요구사항 원문: `.specs/requirements/SRS - Software Requirements Specification.md`

---

## 배경 및 접근 전략

| 문제 | 접근법 |
|------|--------|
| **OLTP 부하 격리** — 관리자 조회를 OLTP DB에 직접 내리면 결제 처리 트래픽과 DB를 경합하여 운영 부하가 가중된다 | OLTP 이벤트를 Kafka로 수신해 조회 전용 Backoffice DB에 동기화하고, 관리자 조회는 이 DB만을 대상으로 한다 |
| **이벤트 페어링 타이밍** — 결제 1건은 원장에 PAYMENT(출금)·RECEIVE(입금) 2개의 이벤트를 발생시킨다. 두 이벤트는 Kafka를 통해 비동기로 전달되므로 도착 순서·시각이 보장되지 않는다. 한쪽만 수신된 상태에서는 정상 처리 여부를 판단할 수 없다 | Consumer가 이벤트 수신 시 같은 `related_id`를 가진 반대편 이벤트의 존재를 확인하여 `pairing_status`(COMPLETE / INCOMPLETE / UNKNOWN)를 갱신한다. 도착 타이밍에 무관하게 페어링 완결 여부를 조회할 수 있다 |

---

## 0) 문서 운영 원칙 (Hybrid)

이 문서는 항목을 다음 3가지 상태로 분리해 기록한다.

1. **As-Is (코드 구현)**
- 현재 저장소 코드로 즉시 검증 가능한 동작/계약

2. **Target (To-Be)**
- 아직 미구현이거나 운영 전환 단계에서 확정할 목표 상태

3. **Out of Scope / Reserved**
- 현재 프로젝트 범위 밖이거나 향후 확장 예약 항목

---

## 1) 프로젝트 목표

### As-Is (코드 구현)

- Admin API는 Backoffice DB를 조회해 관리자 조회 기능을 제공한다.
- Sync Consumer는 이벤트를 소비해 Backoffice DB를 멱등 upsert한다.
- Backoffice DB는 조회 최적화 목적의 **파생(read-optimized) 저장소**로 운영된다.

### Target (To-Be)

- Cloud-Secure 전환 이후에도 동일 API 계약/지표/SLO를 유지한다.
- 운영 자동화(E3)에서 배포-검증-복구 루프를 표준화한다.

### Out of Scope / Reserved

- 결제/정산 쓰기 트랜잭션(Freeze/Settle/Rollback)
- 고객-facing API
- 프로듀서(이벤트 발행) 구현

---

## 2) 책임 경계

### As-Is (코드 구현)

- 본 저장소는 **consumer-only**다. 이벤트 발행 책임은 업스트림 서비스에 있다.
- Backoffice DB 쓰기 경로는 다음 두 컴포넌트로 제한한다.
  - Sync Consumer: 동기화/upsert/DLQ
  - Admin API: 감사로그 저장(`bo.admin_audit_logs`)
- 운영 조회는 Admin API를 통해 수행하며, DB 직접 조회는 운영 절차로만 허용한다.

### Target (To-Be)

- Cloud-Secure에서 네트워크/권한 정책으로 위 책임 경계를 강제한다.

### Out of Scope / Reserved

- 카프카/모니터링 인프라 프로비저닝 자동화 자체는 인프라팀 소유다.

---

## 3) 범위 정의

### As-Is (코드 구현)

- Admin 조회 API 3종
  - `GET /admin/tx/{tx_id}`
  - `GET /admin/payment-orders/{order_id}`
  - `GET /admin/wallets/{wallet_id}/tx`
- Backoffice DB 스키마/마이그레이션
  - `bo.ledger_entries`
  - `bo.payment_orders`
  - `bo.payment_ledger_pairs`
  - `bo.admin_audit_logs`
  - `bo.consumer_dlq_events`
- Sync Consumer
  - profile 기반 topic 매핑
  - alias/core_required 정규화
  - 멱등 upsert + pairing + DLQ
- 관측/감사
  - API/DB/Consumer 메트릭
  - 조회 감사로그 저장

### Target (To-Be)

- E2/E3 단계에서 보안형 운영 승격, 컷오버 자동화, 정기 리허설을 고도화한다.

### Out of Scope / Reserved

- Databricks/Lakehouse 산출물 서빙
- Admin UI 자체 구현

---

## 4) 성공 기준 (상위)

### As-Is (코드 구현)

- 기능 계약
  - `tx_id` 미존재 시 `404`
  - `order_id` 미존재 시 `404`
  - wallet 조회는 빈 목록이어도 `200`
- 페어링 계약
  - `pairing_status`는 `COMPLETE | INCOMPLETE | UNKNOWN`로 응답
- 동기화 계약
  - at-least-once 소비를 멱등 upsert로 수렴
  - LWW 규칙: `updated_at > source_version > (둘 다 없을 때 ingested_at)`
- 감사 계약
  - 성공/404 조회는 `bo.admin_audit_logs`에 기록
  - `result_count` 포함

### Target (To-Be)

- 운영 SLO(목표)
  - API p95 < 200ms
  - 데이터 신선도 p95 < 5s
- Cloud-Secure 게이트 기준의 재현 가능한 E2E 운영 증빙 확보

### Out of Scope / Reserved

- 본 문서는 벤치마크 수치의 실시간 모니터링 결과를 보관하지 않는다.

---

## 5) 상위 아키텍처

### As-Is (코드 구현)

```text
OLTP/Upstream Producer -> Kafka/Event Hubs -> Sync Consumer -> Backoffice DB -> Admin API
```

- Consumer는 profile 기준 토픽을 subscribe하고 payload를 정규화/검증 후 DB upsert한다.
- Admin API는 `ledger_entries + payment_orders + payment_ledger_pairs` 조합으로 응답을 구성한다.

### Target (To-Be)

- Cloud-Secure 환경에서 동일 데이터 흐름을 private network + managed identity 모델로 승격한다.

### Out of Scope / Reserved

- CDC 엔진 세부 운영 정책(예: Debezium 운영 토폴로지)

---

## 6) 보안/인가/감사 정책

### As-Is (코드 구현)

- 인증 모드
  - `AUTH_MODE=disabled` (로컬 개발)
  - `AUTH_MODE=oidc` (JWT 검증)
- 인가
  - `ADMIN_READ` 또는 `ADMIN_AUDIT` 보유 시 조회 허용
- 감사로그
  - API 조회 시 `who/when/what/result/status_code/duration/result_count` 저장
  - `401/403`은 라우트 진입 전 차단될 수 있어 DB 감사로그 대신 인증 계층 로그로 추적

### Target (To-Be)

- 운영형에서 `AUTH_MODE=disabled` 금지
- OIDC/RBAC/감사 추적을 운영 게이트 표준으로 고정

### Out of Scope / Reserved

- IAM 조직 정책 자체 정의

---

## 7) 관측/운영 정책

### As-Is (코드 구현)

- API 지표: `api_request_latency_seconds`, `api_requests_total`, `api_requests_inflight`
- DB 지표: `db_query_latency_seconds`, `db_queries_total`, `db_pool_*`, `db_replication_lag_seconds`
- Consumer 지표: `consumer_messages_total`, `consumer_event_lag_seconds`, `consumer_kafka_lag`, `consumer_freshness_seconds`, `consumer_dlq_total`
- 계약/품질 지표: `consumer_contract_*`, `consumer_version_missing_total`, `pairing_*`
- 알림 레퍼런스: `docker/observability/alert_rules.yml`

### Target (To-Be)

- E2/E3에서 알림 튜닝/운영 절차를 정기 회귀(리허설)와 연동한다.

### Out of Scope / Reserved

- 본 문서에 모니터링 쿼리 결과 원문을 누적 저장하지 않는다.

---

## 8) 단계별 상태 (F/E 축)

### As-Is (코드 구현 + 로드맵 정렬)

- 기능 축
  - F1: Read-only MVP 동작
  - F2: Pairing 강화 동작
  - F3: 품질/운영 게이트 진행 중
- 환경 축
  - E1: Cloud-Test 검증 이력 존재
  - E2: Cloud-Secure 승격 진행 중
  - E3: 운영 자동화 확장 예정

> 세부 상태/증빙은 `.roadmap/implementation_roadmap.md`를 따른다.

### Target (To-Be)

- E2 완료 후 운영형 컷오버 기준을 고정하고 E3 자동화를 마무리한다.

### Out of Scope / Reserved

- 본 문서에서 스프린트 단위 일정은 관리하지 않는다.

---

## 9) 문서 소유권 분리

### As-Is (코드 구현)

- 이 문서(`backoffice_project_specs.md`): 상위 정책/범위/책임/승격 기준
- `.specs/backoffice_db_admin_api.md`: API + DB 계약 SSOT
- `.specs/backoffice_data_project.md`: Consumer + 이벤트 동기화 계약 SSOT

### Target (To-Be)

- 중복 규칙은 하위 SSOT 1곳에만 상세화하고 나머지는 링크 참조로 유지한다.

### Out of Scope / Reserved

- 단일 문서에 모든 구현 세부를 재중복 기술하지 않는다.

---

## 10) Open Issues (실제 미결)

1. 환불/취소/정정(역분개) 타입 확장 시 pairing 규칙을 어떻게 일반화할지
2. `related_type` 다중 도메인 확장 시 `payment_ledger_pairs` 모델을 분리/확장할지
3. `PaymentLedgerPaired` 확정 이벤트를 도입할지(현재는 consume 미지원, reserved)
4. Cloud-Secure 최종 컷오버 시 운영 승인 게이트 산출물 표준을 어디까지 자동화할지

