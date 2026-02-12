# 결정 필요 항목 목록 (Open Decisions)

작성일: 2026-02-06
업데이트: 2026-02-09

## 목적

구현 중 **명확히 결정되지 않았거나 가정으로 처리한 항목**을 기록하고,
결정이 내려지면 본 문서를 갱신한다.

## 업데이트 규칙

- 구현 중 새로운 가정/모호점이 생기면 **즉시 본 문서에 추가**한다.
- 결정이 확정되면 항목을 `결정됨`으로 변경하고 **근거(코드/문서/룰/테이블)** 를 명시한다.

## 결정 필요 항목

### DEC-001 OIDC 클레임 매핑(roles / actor id)

- 상태: **결정됨(2026-02-09)**
- 결정: 역할(Role)은 `roles`+`scp`에서 추출하고, actor id는 `oid` 우선/없으면 `sub`를 사용한다. (`AUTH_ROLES_CLAIM=roles,scp`, `AUTH_ACTOR_ID_CLAIMS=oid,sub`)
- 영향: Admin API 인가(RBAC) 및 감사로그(actor 식별자) 안정성
- 재검토 트리거: Entra 토큰 클레임 형태 변경 또는 게이트웨이 표준 변경
- 근거: `src/api/auth.py`, `tests/unit/test_auth.py`, `configs/README.md`, `configs/env.example`

### DEC-002 DLQ 저장소 baseline(Cloud-Test/local)

- 상태: **결정됨(2026-02-09)**
- 결정: Cloud-Test/local에서는 DLQ를 JSONL 파일(`DLQ_PATH`)에 append 저장한다.
- 영향: 테스트 환경에서는 컨테이너 로컬 파일이므로 내구성이 약하다(테스트 목적 상 허용).
- 재검토 트리거: 운영형 DLQ 정책 확정(DEC-201)
- 근거: `src/consumer/dlq.py`, `src/consumer/main.py`, `configs/env.example`

### DEC-003 `status_group` 매핑

- 상태: **결정됨(2026-02-09)**
- 결정: `payment_orders.status`(원문)을 v1 매핑표로 `status_group(SUCCESS/FAIL/IN_PROGRESS/UNKNOWN)`로 변환한다. 매핑 없는 값은 `UNKNOWN`.
- 영향: Admin 조회에서 상태를 “성공/실패/진행”으로 빠르게 해석 가능
- 재검토 트리거: 업스트림 status taxonomy 확정/변경(운영형 상태 집합 재정의)
- 근거: `src/api/service.py` (`_resolve_status_group`), `tests/unit/test_api_service.py`, `.specs/backoffice_db_admin_api.md`

### DEC-004 페어링 회귀(regression) 방지 정책

- 상태: **결정됨(2026-02-09)**
- 결정: 완성 페어(complete)는 불완전 페어(incomplete)로 덮어쓰지 않는다. (complete -> incomplete 업데이트 차단)
- 영향: out-of-order/부분 데이터 유입 시 페어링 상태가 역전되는 것을 방지
- 재검토 트리거: 환불/정정(역분개) 등으로 “완성 페어가 다시 깨지는” 도메인 정책이 정의될 때
- 근거: `src/consumer/pairing.py` (`should_update_pair`), `tests/unit/test_pairing.py`

### DEC-005 `related_type` 페어링 범위

- 상태: **결정됨(2026-02-09)**
- 결정: 페어링은 `related_type=PAYMENT_ORDER`만 지원한다. 그 외는 `pairing_status=UNKNOWN`.
- 영향: 도메인 확장 전까지 안정적으로 단일 경로 유지
- 재검토 트리거: 다른 related domain 페어링 요구가 생길 때
- 근거: `src/api/service.py` (`_resolve_pairing`, `_resolve_related_type`), `.specs/backoffice_project_specs.md`

### DEC-006 `amount_signed` baseline(Cloud-Test/local)

- 상태: **결정됨(2026-02-09)**
- 결정: 이벤트에 `amount_signed`가 있으면 저장, 없으면 `NULL`로 저장한다(Consumer 파생 없음).
- 영향: 데모/검증에서 돈 의미 오해를 방지하고, 업스트림 계약 부재를 `NULL`로 표현
- 재검토 트리거: 운영형 SSOT 확정(DEC-204)
- 근거: `src/consumer/events.py`, `src/consumer/processor.py`, `configs/topic_checklist.md`

### DEC-007 Slow query 임계치

- 상태: **결정됨(2026-02-09)**
- 결정: slow query 로그 임계치는 기본 `DB_SLOW_QUERY_MS=200`으로 두고, 환경변수로 조정한다.
- 영향: SLO(p95 200ms)와 함께 느린 쿼리 상관관계를 관측 가능
- 재검토 트리거: 운영 환경의 p95 목표/DB 성능 프로파일 변경 시
- 근거: `src/common/config.py`, `configs/README.md`, `.specs/backoffice_project_specs.md`

### DEC-008 Freshness baseline(Cloud-Test/local)

- 상태: **결정됨(2026-02-09)**
- 결정: Consumer freshness는 도메인 시각을 기준으로 측정한다. ledger=`event_time`, order=`updated_at` 없으면 `created_at`.
- 영향: commit-time이 없더라도 일관된 “마지막 이벤트 기준” 신선도 지표 확보
- 재검토 트리거: commit-time/occurred_at 제공이 표준화될 때(운영형 기준 전환)
- 근거: `src/consumer/main.py`, `src/consumer/metrics.py`, `.specs/backoffice_data_project.md`

### DEC-009 Correlation ID 헤더

- 상태: **결정됨(2026-02-09)**
- 결정: 표준 헤더는 `X-Correlation-ID`로 한다. API는 해당 헤더를 응답에 포함하며, consumer는 헤더/페이로드의 alias를 허용한다.
- 영향: API/Consumer 로그 상관관계(tracing-lite) 확보
- 재검토 트리거: 조직 표준 헤더가 별도로 확정될 때
- 근거: `src/common/observability.py`, `src/api/observability.py`

### DEC-010 알림 임계치 baseline(Phase 8/9)

- 상태: **결정됨(2026-02-09)**
- 결정: baseline alert rule을 채택한다(API p95>200ms/5m, error rate(4xx/5xx)>2%/5m, freshness>5s/5m, DLQ activity>0/5m).
- 영향: 최소 운영 알림(데모/검증) 기준을 단일 세트로 유지
- 재검토 트리거: 온콜/운영 체계가 생기면 4xx 분리 및 severity 재설계
- 근거: `docker/observability/alert_rules.yml`, `README.md`

### DEC-101 OIDC provider

- 상태: **결정됨(2026-02-09)**
- 결정: OIDC provider는 Microsoft Entra ID를 사용한다.
- 영향: auth discovery/issuer/jwks/audience 기준이 Entra 형태에 맞춰짐
- 근거: `configs/README.md`

### DEC-102 Audit log 저장소

- 상태: **결정됨(2026-02-09)**
- 결정: Admin API 조회 감사로그는 `bo.admin_audit_logs` 테이블에 저장한다.
- 영향: 조회 이력 감사/추적 가능
- 근거: `src/db/models.py`, `migrations/20260205_0003_create_admin_audit_logs.py`

### DEC-103 페어링 저장소

- 상태: **결정됨(2026-02-09)**
- 결정: 페어링 결과는 Backoffice DB의 `bo.payment_ledger_pairs`에 저장한다.
- 영향: API 조회에서 빠른 페어링 조회 가능
- 근거: `migrations/20260205_0001_create_backoffice_schema.py`

### DEC-104 Event Hubs 소유 모델

- 상태: **결정됨(2026-02-09) → 수정됨(2026-02-10)**
- 결정(Phase 8): Cloud-Test는 owner별로 분리된 Event Hubs namespace를 사용했다.
- 결정(Phase 9 이후): 기존 공유 Event Hubs namespace를 활용한다. tx-lookup-service는 토픽(hub)만 소유하고, namespace는 생성하지 않는다.
- 영향: 리소스 중복 제거, 운영 일관성 확보
- 근거: `.roadmap/implementation_roadmap.md`, `.specs/cloud_migration_rebuild_plan.md`, 전체 아키텍처 다이어그램

### DEC-105 Cloud 런타임

- 상태: **결정됨(2026-02-09) → 수정됨(2026-02-10)**
- 결정(Phase 8): Cloud-Test는 `Event Hubs(Kafka) + Azure Container Apps`로 구성했다.
- 결정(Phase 9 이후): Cloud-Secure는 `Event Hubs(Kafka) + AKS(RG 공유 클러스터)`로 구성한다. tx-lookup-service는 공유 AKS 클러스터에 namespace 분리 배포한다.
- 영향: AKS를 조직 표준 실행 환경으로 채택, Container Apps는 Phase 8 테스트 한정
- 근거: `.roadmap/implementation_roadmap.md`, `.specs/cloud_phase8_execution_report.md`, 전체 아키텍처 다이어그램

### DEC-106 Cloud-Test 시크릿 전달

- 상태: **결정됨(2026-02-09)**
- 결정: Cloud-Test는 SAS/env 주입을 우선하고, Key Vault + Managed Identity는 secure rebuild 단계로 이연한다.
- 영향: 테스트 속도 우선(보안 하드닝은 별도 환경에서)
- 근거: `.specs/cloud_migration_rebuild_plan.md`

### DEC-107 Event Hubs baseline contract(Phase 8 test)

- 상태: **결정됨(2026-02-09)**
- 결정: hubs=`ledger.entry.upserted`, `payment.order.upserted`; partition=2; retention=3d; consumer group naming=`bo-sync-<env>-<owner>-v1`.
- 영향: 프로비저닝/배포 자동화가 계약값에 의존
- 근거: `.specs/cloud_migration_rebuild_plan.md`, `.specs/cloud_phase8_execution_report.md`

### DEC-108 Cloud 승격 모델

- 상태: **결정됨(2026-02-09)**
- 결정: Cloud-Test(disposable/public) -> Cloud-Secure(separate/secured) 2단계 승격, in-place hardening 금지.
- 영향: 보안 적용은 별도 리소스에서 재검증 후 컷오버
- 근거: `.specs/cloud_migration_rebuild_plan.md`, `.specs/backoffice_project_specs.md`

### DEC-109 Container Apps test naming

- 상태: **결정됨(2026-02-09)**
- 결정: `team4-txlookup-*` 패턴을 유지하되, Container Apps 계열은 32자 제한으로 축약 패턴을 사용한다.
- 영향: Azure naming limit 회피
- 근거: `.specs/cloud_migration_rebuild_plan.md`, ~~`scripts/cloud/phase8/provision_resources.sh`~~ (제거됨), `.specs/cloud_phase8_execution_report.md`

### DEC-110 Destroy/Recreate test under RG lock

- 상태: **결정됨(2026-02-09)**
- 결정: RG lock으로 delete가 막히면 consumer scale cycle(`min 1 -> 0 -> 1`)로 recreate를 대체 검증한다.
- 영향: lock 환경에서도 파이프라인 복구 동선 확보
- 근거: ~~`scripts/cloud/phase8/destroy_recreate_check.sh`~~ (제거됨), `.specs/cloud_phase8_execution_report.md`

### DEC-111 Azure 리소스 소유 모델(Cloud-Secure)

- 상태: **결정됨(2026-02-10)**
- 결정: tx-lookup-service의 Azure 리소스를 아래와 같이 분류한다.
  - **서비스 전용**: Azure Database for PostgreSQL Flexible Server (Backoffice Serving DB)
  - **RG 공유**: AKS(클러스터), ACR, Key Vault, App Insights, Log Analytics
  - **기존 활용**: Event Hubs namespace(이미 존재, 토픽만 소유)
  - **플랫폼 소유**: App Gateway, Bastion, Firewall, VNet, Private DNS Zone
  - **비범위**: Confidential Ledger(CryptoSvc), SQL Database(AccountSvc), Databricks, ADLS Gen2
- 영향: 리소스 생성은 인프라팀이 수행한다. 이 레포는 네이밍 컨벤션과 리소스 요구사항만 정의하고 인프라팀에 전달한다.
- 근거: 전체 아키텍처 다이어그램 분석, `.specs/backoffice_project_specs.md` 10.3항, `.specs/cloud_migration_rebuild_plan.md`

### DEC-201 DLQ 저장소(Cloud-Secure/Prod)

- 상태: **결정됨(2026-02-09)**
- 결정: 운영형 DLQ는 PostgreSQL 테이블(`bo.consumer_dlq_events`)에 저장하고, 기본 보관기간은 14일로 한다. 재처리는 수동 replay(선택/범위)로 재실행한다.
- 영향: 인프라 추가 없이 데모/검증용 운영 동선(SQL triage + replay) 확보
- 재검토 트리거: Kafka/Event Hubs DLQ 토픽을 운영 표준으로 채택할 때
- 근거: `src/consumer/main.py`(DLQ write + commit), `src/consumer/dlq.py`(baseline), `docker/observability/alert_rules.yml`

### DEC-202 알림 임계치/심각도(Cloud-Secure/Prod)

- 상태: **결정됨(2026-02-09)**
- 결정: 운영 알림도 baseline rule을 그대로 채택한다(튜닝 유예). `DataFreshnessHigh=critical`, 나머지=warning.
- 영향: 정책 논쟁을 피하고, 문서/구현 불일치 최소화
- 재검토 트리거: 실제 트래픽/온콜 체계 도입 시(4xx 분리, DLQ 2단계 severity 등)
- 근거: `docker/observability/alert_rules.yml`, `README.md`

### DEC-203 Entra OIDC 클레임 매핑(roles / actor id)

- 상태: **결정됨(2026-02-09)**
- 결정: Entra 토큰을 고려해 `roles,scp`에서 role을, `oid,sub`에서 actor id를 추출한다(환경변수 오버라이드 가능).
- 영향: 역할/식별자 클레임 차이로 인한 인증 실패 가능성을 낮춤
- 근거: `src/api/auth.py`, `configs/README.md`, `configs/env.example`, `tests/unit/test_auth.py`

### DEC-204 `amount_signed` SSOT(운영)

- 상태: **결정됨(2026-02-09)**
- 결정: `amount_signed`는 업스트림 제공 값을 SSOT로 저장한다. 미제공 시 Consumer는 파생하지 않고 `NULL`로 저장한다.
- 영향: 부호 규칙 오해로 인한 money semantics 오류 위험을 최소화
- 재검토 트리거: 업스트림이 `entry_type` 확장/표준 부호 계약을 제공할 때(파생 전환 검토)
- 근거: `src/consumer/events.py`, `src/consumer/processor.py`, `configs/topic_checklist.md`, `.specs/backoffice_db_admin_api.md`

### DEC-205 Freshness 기준 시각(운영)

- 상태: **결정됨(2026-02-09)**
- 결정: Consumer freshness는 도메인 시각을 기준으로 한다(ledger=`event_time`, order=`updated_at||created_at`). API `data_lag_sec`는 `now - max(ingested_at, event_time)`로 계산한다.
- 영향: commit-time 부재 상황에서도 일관된 신선도/지연 해석 가능
- 재검토 트리거: commit-time/occurred_at가 이벤트 계약으로 확정될 때
- 근거: `src/consumer/main.py`, `src/consumer/metrics.py`, `src/api/service.py`, `.specs/backoffice_db_admin_api.md`

### DEC-206 `status_group` 매핑 v1

- 상태: **결정됨(2026-02-09)**
- 결정: `payment_orders.status` 원문은 유지하고, 아래 v1 매핑표로 `status_group`를 계산한다(대소문자 무시).
- 매핑표(v1): `SUCCESS=SETTLED,COMPLETED,SUCCESS,SUCCEEDED,PAID` / `FAIL=FAILED,CANCELLED,CANCELED,REJECTED,DECLINED` / `IN_PROGRESS=CREATED,PENDING,PROCESSING,AUTHORIZED` / 그 외 또는 NULL은 `UNKNOWN`
- 영향: 운영/CS가 상태를 그룹 단위로 빠르게 해석 가능
- 재검토 트리거: status taxonomy 확정/변경 시 v2 매핑으로 재정의
- 근거: `src/api/service.py`, `tests/unit/test_api_service.py`, `.specs/backoffice_project_specs.md`, `.specs/backoffice_db_admin_api.md`

### DEC-112 이벤트 발행 책임 분리

- 상태: **결정됨(2026-02-12)**
- 결정: 카프카 프로듀서 코드(이벤트 발행)는 업스트림 서비스(CryptoSvc, AccountSvc, CommerceSvc)가 소유한다. tx-lookup-service는 컨슈머 전용이다. 카프카/모니터링 인프라 프로비저닝은 인프라팀이 수행한다.
- 영향: Phase 8 프로비저닝 스크립트(`scripts/cloud/phase8/`) 제거. 이벤트 계약(스키마)은 `configs/topic_checklist.md`에서 정의하고 업스트림 팀에 전달한다.
- 근거: 팀 간 업무 범위 조정, `.specs/backoffice_project_specs.md` 10.3항, `.specs/entire_architecture.md`
