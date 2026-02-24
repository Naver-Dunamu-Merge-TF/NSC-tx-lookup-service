# F/E 축 기반 구현 로드맵 (SSOT 파생)

Last updated: 2026-02-24

> 본 문서는 SSOT 문서 기준으로 현재 구현 상태를 요약한 파생 로드맵이다.
> 기존 `Phase 1~11` 참조는 본 개정에서 폐기한다.

## 1) 기준 문서 / 판정 규칙

### 1.1 기준 문서
- `.specs/backoffice_project_specs.md`
- `.specs/backoffice_db_admin_api.md`
- `.specs/backoffice_data_project.md`
- `.specs/infra/cloud_migration_rebuild_plan.md`
- `.specs/decision_open_items.md`
- `.specs/archive/cloud_phase8_execution_report.md`
- `README.md`

### 1.2 판정 규칙
- 상태는 `COMPLETE`, `IN PROGRESS`, `NOT STARTED` 3단계로만 표기한다.
- 상태 근거는 SSOT 문서 + 코드/테스트 증빙 + DEC 결과를 우선 적용한다.
- 기준 시점은 워킹트리 문서 상태(2026-02-23)다.
- 일정 날짜/스프린트는 두지 않고, 게이트(진입/완료 조건) 기준으로만 관리한다.
- `DEC-225` 기준: 문서-실자원 드리프트는 F-track 개발의 차단 사유가 아니며, 정렬은 E2(Stage B) 게이트에서 수행한다.
- AKS/클러스터 내 검증은 F3 품질 게이트에 포함하며, E2 진입 전에 최소 1회 선행 완료를 요구한다.

## 2) 상태 스냅샷

| Stage | Status | 근거 문서 |
| --- | --- | --- |
| F1 | COMPLETE | `.specs/backoffice_project_specs.md` 9.1, `src/api/main.py`, `tests/e2e/test_admin_tx_e2e.py` |
| F2 | COMPLETE | `.specs/backoffice_project_specs.md` 9.1, `.specs/decision_open_items.md` DEC-211/216, `src/consumer/pairing.py` |
| F3 | IN PROGRESS | `.specs/backoffice_project_specs.md` 9.1, `.specs/backoffice_project_specs.md` 11, `.specs/backoffice_data_project.md` 11 |
| E1 | COMPLETE | `.specs/backoffice_project_specs.md` 9.2, `.specs/archive/cloud_phase8_execution_report.md`, `.specs/infra/cloud_migration_rebuild_plan.md` 3.1 |
| E2 | IN PROGRESS | `.specs/backoffice_project_specs.md` 9.2, `.specs/infra/cloud_migration_rebuild_plan.md` 3.2(Stage B), `.agents/logs/verification/20260225_e2_1_drift_inventory/` |
| E3 | NOT STARTED | `.specs/backoffice_project_specs.md` 9.2, `.specs/infra/cloud_migration_rebuild_plan.md` 3.2(Stage C) |

## 3) 완료 단계 요약 (짧게)

### F1 — COMPLETE
- Backoffice DB + Admin API read path가 운영 기준으로 동작한다.
- API 기준선 3종(`GET /admin/tx/{tx_id}`, `GET /admin/payment-orders/{order_id}`, `GET /admin/wallets/{wallet_id}/tx`)이 구현되어 있다.
- 감사로그 `bo.admin_audit_logs.result_count` 반영까지 완료됐다.

### F2 — COMPLETE
- `bo.payment_ledger_pairs` 기반 페어링 경로와 품질 보정(반대 타입 필터, 회귀 방지, 범위 제한)이 적용됐다.

### E1 — COMPLETE
- Cloud-Test(E1) E2E 스모크 및 재생성 검증이 완료됐고 결과가 아카이브 문서에 정리돼 있다.

## 4) 미완료 단계 실행 백로그 (대형 태스크 + 세부 태스크)

- 분류 태그:
  - `[분류: 최소동작 필수]`: AKS 기본 동작 확인 + E2 진입 차단 해제를 위한 필수 작업
  - `[분류: 운영/권장]`: 운영 안정화/고도화 목적 작업(현 단계 기준)

### F3 — IN PROGRESS

#### 대형 태스크 F3-1: 상태/버전 이벤트 계약 표준화
- [x] `payment_orders.status` 운영 표준 집합(v2) 확정 및 `status_group` 매핑표 동결
- [x] 토픽별 필수 메타(`updated_at` 또는 `version`) 제공률 기준 합의
- [x] 프로파일 매핑(`EVENT_PROFILE_ID`) 운영 규칙과 계약 성숙도 지표(`consumer_contract_*`, `consumer_version_missing_total`) 기준선 고정
- [x] `configs/topic_checklist.md` 계약 문구 갱신 및 업스트림 전달 기록
- [x] 표준화 결과를 `.specs/backoffice_project_specs.md`/`.specs/backoffice_data_project.md`에 반영
- 근거(결정): `.specs/decision_open_items.md` (`DEC-229`, `DEC-230`, `DEC-231`)
- 근거(계약 문구): `configs/topic_checklist.md`
- 근거(전달 기록): `.specs/upstream_event_contract_handoff_log.md`
- 근거(검증 로그): `.agents/logs/verification/20260224_015153_f3_1_contract_standardization/`

#### 대형 태스크 F3-2: SLO 알림 규칙 운영 적용
- [x] `docker/observability/alert_rules.yml`의 규칙을 실제 알림 플랫폼(Azure Monitor) 규칙으로 이식
- [x] `api_request_latency_seconds`, `consumer_freshness_seconds`, `db_pool_*`, `db_replication_lag_seconds` 대시보드 연결
- [x] 임계치 튜닝(오탐/미탐 점검)과 severity 운영안 확정
- [x] 알림 발생 -> 조치 -> 복구까지 운영 증빙 로그 확보
- 근거(운영 런북): `docs/ops/f3_2_slo_alerts_runbook.md`
- 근거(결정): `.specs/decision_open_items.md` (`DEC-232`, `DEC-233`, `DEC-234`)
- 근거(검증 로그): `.agents/logs/verification/20260224_021748_f3_2_slo_alert_ops/`
- 운영안 요약:
  - severity는 `DEC-202` baseline을 유지한다(`DataFreshnessHigh`, `DbReplicationLagHigh`만 `critical`).
  - 임계치 튜닝은 3일 관측 증빙 후 오탐/미탐 근거가 있을 때만 수행한다.
  - Azure Monitor KQL 기준은 workspace-based `AppMetrics`로 고정한다.
  - Action Group 채널은 플랫폼팀 관리, 본 저장소는 `ACTION_GROUP_ID` 인터페이스만 관리한다.

#### 대형 태스크 F3-3: 품질 게이트 마감
- [x] L2 게이트(`.venv/bin/python -m pytest --cov-fail-under=80`) 정기 통과 상태 확보
- [x] 페어링/상태 변경 관련 L3 스모크 기준 시나리오 확정 (AKS/클러스터 내 실행 포함)
- [x] AKS/클러스터 내 검증 수행 및 증빙 확보 (E2 진입 전 최소 1회, 이후 정기 회귀) `[분류: 최소동작 필수]`
- [x] F3 완료 판정 체크리스트(계약, 알림, 테스트) 문서화
- 상태 메모: `CONDITIONAL (L3 deferred by DEC-226)` / E2 진입은 L3 pass 증빙 전까지 차단
- 실행 방식(고정):
  - 서브에이전트 루프 고정: `Implementer -> Spec Reviewer -> Code Quality Reviewer -> Fix/Re-review`
  - 근거(운영 런북): `docs/ops/f3_3_quality_gate_runbook.md`
  - 근거(점프박스 런북): `docs/ops/f3_3_aks_jumpbox_runbook.md`
  - 근거(점프박스 teardown): `docs/ops/f3_3_aks_jumpbox_teardown_runbook.md`
  - 근거(L3 시나리오): `docs/ops/f3_3_l3_cluster_smoke_scenarios.md`
  - 근거(완료 체크리스트): `docs/ops/f3_3_closeout_checklist.md`
  - 근거(결정): `.specs/decision_open_items.md` (`DEC-226`, `DEC-235`)
  - 근거(검증 로그): `.agents/logs/verification/20260223_174702_f3_3_task1/`, `.agents/logs/verification/20260223_174800_f3_3_task2/`, `.agents/logs/verification/20260223_174856_f3_3_task3/`, `.agents/logs/verification/20260223_175009_f3_3_task4/`, `.agents/logs/verification/20260223_175121_f3_3_task5/`
  - 근거(L3 조건부 증빙): `.agents/logs/verification/20260223_175150_f3_3_l3_blocked/`
  - 근거(L3 pass 증빙): `.agents/logs/verification/20260224_075536_f3_3_l3_pass/`
  - 근거(점프박스 파일럿 증빙): `.agents/logs/verification/20260224_012413_f3_3_jumpbox_pilot/`
  - 정기 회귀 cadence: F3 closeout 이후 주 1회 또는 E2 진입 전 사전 실행

#### 대형 태스크 F3-4: AKS 조기 검증 트랙
- [x] AKS 상태 안정화 확인(`provisioningState=Succeeded`) 및 `txlookup` namespace 준비 `[분류: 최소동작 필수]`
- [x] API/Consumer 이미지 pull + 기동 스모크 (DB/Event Hubs 연결 확인) `[분류: 최소동작 필수]`
- [x] 클러스터 내 `GET /admin/tx/{tx_id}` 200/404 스모크 + consumer lag/freshness 점검 `[분류: 최소동작 필수]`
- [x] 실패 케이스 분류(runbook)와 재시도 기준 문서화 `[분류: 운영/권장]`
- 상태 메모: `COMPLETE (task2 startup/connectivity pass, task3 API 404/200 pass, task4 lag/freshness evidence pass; infra preaction 이후 잔여 이슈였던 consumer_kafka_lag 미수집은 watermark 계측 경로 보강 후 회복)`
- 실행 방식(고정):
  - 근거(운영 런북): `docs/ops/f3_4_aks_early_validation_runbook.md`
  - 근거(증빙 템플릿): `docs/ops/f3_4_validation_evidence_template.md`
  - 근거(결정): `.specs/decision_open_items.md` (`DEC-237`, `DEC-239`, `DEC-240`)
- 근거(검증 로그): `.agents/logs/verification/20260224_100242_f3_4_runtime_status_check/`, `.agents/logs/verification/20260224_101159_f3_4_closeout/`, `.agents/logs/verification/20260224_103700_f3_4_runtime_closeout/`, `.agents/logs/verification/20260224_110000_f3_4_runtime_recovery/`, `.agents/logs/verification/20260224_113527_f3_4_metric_recovery/`, `.agents/logs/verification/20260224_143303_f3_4_infra_preaction/`, `.agents/logs/verification/20260224_145812_f3_4_kafka_lag_recovery/`
- 관측 스냅샷:
  - AKS `provisioningState=Succeeded`, `txlookup` namespace `Active`
  - `txlookup` namespace 배포 확인: `tx-lookup-api`, `txlookup-postgres`
  - recovery run에서 `txlookup-consumer` 배포/파드 기동 확인 (image=`txlookup/api:<tag>`, command=`python -m src.consumer.main consume`)
  - DB/Event Hubs 연결 확인 로그 확보(`db_connectivity_ok`, `eventhubs_tcp_ok`)
  - API smoke 재시도 결과: `404`/`200` 모두 확인
  - infra preaction에서 Firewall rule `allow-appinsights-telemetry`를 추가하고 AppInsights 관련 FQDN deny를 allow로 전환 확인
  - preaction 이후 pod TLS handshake(`in.applicationinsights`, `dc.services.visualstudio.com`) 성공, AppMetrics에 `consumer_freshness_seconds`, `consumer_messages_total`, `consumer_event_lag_seconds` 재유입 확인
  - `consumer_kafka_lag` 복구 확인: AppMetrics 30m 질의에서 row 재발생(`max_lag=0`, rows>0) 및 metric inventory에 `consumer_kafka_lag` 포함
- unblock criteria: `provisioningState=Succeeded`, `txlookup namespace ready`, `API 200/404 smoke pass`, `lag/freshness evidence pass`

### E2 — IN PROGRESS

#### 대형 태스크 E2-1: Cloud-Secure 리소스 준비(보안형)
- [x] 인프라팀에 서비스 전용/공유 리소스 요청서 제출(PostgreSQL 전용 + AKS/ACR/Key Vault 공유 모델) `[분류: 운영/권장]`
- [x] AKS 클러스터 배포 경로(네임스페이스, 권한, 네트워크) 선행 검증 결과 반영 `[분류: 운영/권장]`
- [x] 문서 기준 대비 실제 Azure 리소스 드리프트(public/private, access rule, provisioning state) 목록화 `[분류: 운영/권장]`
- 상태 메모: `IN PROGRESS` — 리소스 기프로비저닝 확인, F3-4 AKS 검증 결과 반영 완료, 드리프트 목록화 완료(2026-02-25). 잔여: 네트워크 명세 확정(PG/EVH/ACR public access 결정), 드리프트 정렬 인프라팀 협의 필요.
- 근거(드리프트 목록): `.agents/logs/verification/20260225_e2_1_drift_inventory/`
- 근거(AKS 배포 경로): `.agents/logs/verification/20260224_075536_f3_3_l3_pass/`, `.agents/logs/verification/20260224_145812_f3_4_kafka_lag_recovery/`

#### 대형 태스크 E2-2: 시크릿/권한 전환
- [x] SAS/env 기반 전달에서 Key Vault + Managed Identity 방식으로 전환 설계 `[분류: 운영/권장]`
- [x] 최소권한 RBAC 매트릭스(DB/Event Hubs/AKS/Key Vault) 확정 `[분류: 운영/권장]`
- [x] 접근 실패(401/403/권한오류) 관측 경로와 감사 경로 분리 정의 `[분류: 운영/권장]`
- 상태 메모: `COMPLETE (design/ops gate, dev-first)` — 앱 런타임 코드 변경 없이 문서 계약/증빙 템플릿/결정문서 정렬 완료. Event Hubs는 external ownership 경계로 고정해 E2-2 범위에서 리소스/인증 정책 변경을 수행하지 않음.
- 근거(운영 런북): `docs/ops/e2_2_secret_identity_transition_runbook.md`
- 근거(RBAC 매트릭스): `docs/ops/e2_2_rbac_matrix.md`
- 근거(관측 분리 런북): `docs/ops/e2_2_auth_failure_observability_runbook.md`
- 근거(증빙 템플릿): `docs/ops/e2_2_validation_evidence_template.md`
- 근거(결정): `.specs/decision_open_items.md` (`DEC-242`, `DEC-243`, `DEC-244`)
- 근거(검증 로그): `.agents/logs/verification/20260224_155032_e2_2_secret_rbac_gate/`

#### 대형 태스크 E2-3: 재적재/컷오버 리허설
- [x] `alembic upgrade head -> backfill -> consumer sync` 순서 리허설 `[분류: 운영/권장]`
- [x] `GET /admin/tx/{tx_id}` 200/404 스모크 + 멱등 재처리 검증 `[분류: 운영/권장]`
- [x] 컷오버 시점(`T_cutover`) 및 롤백 의사결정 기준 문서화 `[분류: 운영/권장]`
- 상태 메모: `COMPLETE (jumpbox-path rehearsal pass, canonical idempotency hash)` — private AKS 점프박스 경유로 E2-3 리허설 게이트를 통과했고 GO 판정 증빙을 확보했다.
- 실행 방식(고정):
  - 근거(운영 런북): `docs/ops/e2_3_reload_cutover_rehearsal_runbook.md`
  - 근거(컷오버/롤백 매트릭스): `docs/ops/e2_3_cutover_rollback_decision_matrix.md`
  - 근거(증빙 템플릿): `docs/ops/e2_3_validation_evidence_template.md`
  - 근거(결정): `.specs/decision_open_items.md` (`DEC-245`, `DEC-246`)
  - 근거(검증 로그): `.agents/logs/verification/<timestamp>_e2_3_reload_cutover_rehearsal/`
- 운영 기준:
  - `T_cutover`는 UTC ISO8601 + `+/-5m` 완충창으로 고정한다.
  - backfill 범위는 `T_cutover` 이전, consumer sync 범위는 `T_cutover` 이후로 분리한다.
  - idempotency 비교는 `event_time`, `data_lag_sec` 제외 canonical payload hash 기준으로 고정한다.
- 최신 실행 결과(2026-02-24 UTC):
  - `NO_GO (ENVIRONMENT_BLOCKED)` — 로컬 direct `kubectl` 경로에서 AKS private API FQDN DNS 해석 실패(`no such host`).
  - `NO_GO (IDEMPOTENCY_FAILED)` — full payload hash 비교 시 `event_time`, `data_lag_sec` 변동으로 false negative 발생.
  - `GO (NONE)` — 점프박스 경유 + canonical hash 기준 리허설에서 migration/backfill/sync/smoke/idempotency 게이트 모두 통과.
- 근거(초기 차단 증빙): `.agents/logs/verification/20260224_161208_e2_3_reload_cutover_rehearsal/`
- 근거(해시 기준 보정 전 NO_GO): `.agents/logs/verification/20260224_170327_e2_3_reload_cutover_rehearsal/`
- 근거(최종 통과 증빙): `.agents/logs/verification/20260224_171350_e2_3_reload_cutover_rehearsal/`

#### 대형 태스크 E2-4: 승인 게이트
- [ ] 보안 통제 체크(네트워크/시크릿/권한) 통과 증빙 확보 `[분류: 운영/권장]`
- [ ] 데이터 신선도/API 지연 SLO 재검증 결과 확보 `[분류: 운영/권장]`
- [ ] E2 완료 승인 레코드(결재/리뷰 로그) 저장 `[분류: 운영/권장]`
- [ ] `DEC-225` 드리프트 정렬 완료 확인(체크리스트 + 검증 로그 링크) `[분류: 운영/권장]`

### E3 — NOT STARTED

#### 대형 태스크 E3-1: CI 게이트 구축
- [ ] PR 게이트에 lint + unit + integration + coverage(>=80) 구성 `[분류: 운영/권장]`
- [ ] `.venv` 기준 검증 명령 고정 및 실패 시 로그 아카이브 자동화 `[분류: 운영/권장]`
- [ ] 계약 드리프트 방지 테스트(`tests/unit/test_alert_rules.py` 등) 상시 실행 편입 `[분류: 운영/권장]`

#### 대형 태스크 E3-2: CD 파이프라인 구축
- [ ] build/scan -> migration -> deploy -> smoke 단계 정의 `[분류: 운영/권장]`
- [ ] 배포 중단 조건(마이그레이션 실패, 스모크 실패)과 자동 롤백 기준 정의 `[분류: 운영/권장]`
- [ ] Cloud-Test 통과 결과를 Cloud-Secure 반영 게이트로 연동 `[분류: 운영/권장]`

#### 대형 태스크 E3-3: 운영 복구 체계 운영화
- [ ] DLQ replay/runbook/backfill 절차를 운영 문서로 고정 `[분류: 운영/권장]`
- [ ] 장애/데이터 불일치 대응 체크리스트와 책임자/연락 체계 명시 `[분류: 운영/권장]`
- [ ] 정기 복구 훈련(리플레이/재동기화) 일정 및 증빙 방식 확정 `[분류: 운영/권장]`

#### 대형 태스크 E3-4: 이벤트 계약 테스트 자동화
- [ ] 토픽 필수 필드 계약 테스트를 CI 파이프라인에 통합 `[분류: 운영/권장]`
- [ ] 계약 불일치 시 fail-fast 규칙과 알림 채널 정의 `[분류: 운영/권장]`
- [ ] 업스트림 계약 변경 시 추적 가능한 변경 이력 정책 확정 `[분류: 운영/권장]`

## 5) 미완료 단계 최소 완료 게이트

| Stage | 최소 완료 게이트 |
| --- | --- |
| F3 (IN PROGRESS) | 상태/버전 이벤트 계약 표준화 완료 + 알림 규칙 운영 적용 증빙 + L2/L3(클러스터 내) 검증 체계 고정 + AKS 조기 검증 트랙 완료 |
| E2 (NOT STARTED) | Cloud-Secure 리소스/보안 통제 준비 완료 + 재적재/스모크 리허설 완료 + 컷오버/롤백 기준 승인 |
| E3 (NOT STARTED) | CI/CD 자동화 파이프라인 동작 + 운영 복구 체계 문서/훈련 완료 + 계약 테스트 CI 상시화 |

## 6) 검증 증빙 경로

- DEC 통합 검증: `.agents/logs/verification/dec207_214/`
- 관측성 후속 검증: `.agents/logs/verification/bundle_d_followup_20260212/`
- 본 로드맵 개정 검증 로그:
  - `.agents/logs/verification/20260212_fe_roadmap_refresh_l0_py_compile.log`
  - `.agents/logs/verification/20260212_fe_roadmap_refresh_structure_check.log`
  - `.agents/logs/verification/20260212_fe_roadmap_enhance_l0_py_compile.log`
  - `.agents/logs/verification/20260212_fe_roadmap_enhance_structure_check.log`
  - `.agents/logs/verification/20260224_000257_roadmap_aks_reenable_l0_py_compile.log`
  - `.agents/logs/verification/20260224_011800_roadmap_task_classification_l0_py_compile.log`
  - `.agents/logs/verification/20260224_023600_f3_3_plan_doc_l0_py_compile.log`
