# 구현 계획표 (2026-02-05)

## 기준 문서
- `.specs/backoffice_project_specs.md`
- `.specs/backoffice_db_admin_api.md`
- `.specs/backoffice_data_project.md`
- `README.md`

## Phase 1 — 리포지토리 골격 + 공통 기반
- [x] `src/api`, `src/consumer`, `src/db`, `src/common`, `tests/unit`, `tests/integration`, `migrations`, `configs`, `docker` 디렉터리 생성
- [x] 공통 설정 로딩(환경변수/시크릿) 스켈레톤 및 기본 로깅 포맷 확정
- [x] (Local) `docker compose` 스켈레톤: PostgreSQL + Kafka(or Event Hub emulator 대체) 부팅
- [x] 개발/운영 환경 구분(`local/dev/prod`) 기본 규칙 문서화
- [x] Commit

## Phase 2 — Backoffice DB 스키마 + 마이그레이션
- [x] `bo.ledger_entries`, `bo.payment_orders`, `bo.payment_ledger_pairs` 스키마 정의 및 인덱스 설계
- [x] Alembic 마이그레이션 초안 생성 및 롤백 규칙 확정
- [x] 공통 DB 접근 레이어(연결 풀/세션) 및 upsert 헬퍼 구축
- [x] (Local) 로컬 DB 마이그레이션 적용 및 샘플 데이터 seed 스크립트 추가
- [x] (옵션) `bo.admin_tx_search` 뷰/테이블 필요성 결정 및 설계 초안 (Phase 5 API 쿼리 패턴 확정 후 재검토)
- [x] Commit

## Phase 3 — 초기 적재(Backfill) + Sync Consumer 기본 동작
- [x] 초기 적재(backfill) 범위/기간 정의 및 스크립트 설계
- [x] backfill 실행 경로 구현(덤프 적재 또는 배치 모드)
- [x] 이벤트 스키마 모델(`LedgerEntryUpserted`, `PaymentOrderUpserted`) 정의
- [x] Kafka consumer 루프 및 역직렬화/검증 파이프라인 구현
- [x] 멱등 upsert 로직 구현(`tx_id`, `order_id`) + `updated_at/version` 최신판 정책
- [x] `updated_at/version` 부재 시 `ingested_at` 기준 LWW 정책 적용
- [x] `ingested_at` 기록 및 `version_missing_cnt` 지표 산출
- [x] DLQ 기본 처리(파일/토픽/테이블 중 1개 선택) 스켈레톤
- [x] (Local) 샘플 이벤트 퍼블리셔 및 재처리 시나리오 테스트
- [x] 통합 테스트용 토픽/필수 필드 체크리스트 검증 및 샘플 메시지 확보
- [x] Commit

## Phase 4 — 페어링 테이블 + 품질 지표
- [x] `related_id` 기준 페어링 계산(부분 완성 허용) 로직 구현
- [x] `bo.payment_ledger_pairs` 업데이트/보정 정책 정의
- [x] `pair_incomplete` 비율/지연 시간 산출 지표 추가
- [x] out-of-order 이벤트에 대한 페어링 안정성 테스트
- [ ] Commit

## Phase 5 — Admin API Read-only MVP
- [ ] FastAPI 앱 스켈레톤 및 `GET /admin/tx/{tx_id}` 구현
- [ ] 페어링 불완전 처리: `pairing_status`, `paired_tx_id`, `data_lag_sec` 계산
- [ ] `tx_id` 미존재 시 404 응답 정책 반영
- [ ] `related_type` 기본값(`PAYMENT_ORDER`/`UNKNOWN`) 및 `status_group=UNKNOWN` 기본값 처리
- [ ] (권장) `GET /admin/payment-orders/{order_id}` / `GET /admin/wallets/{wallet_id}/tx` 초안
- [ ] DB 쿼리 경로 최적화(인덱스 사용 확인, N+1 제거)
- [ ] (Local) API ↔ DB ↔ Consumer E2E 스모크 테스트
- [ ] Commit

## Phase 6 — 인증/인가 + 감사 로그
- [ ] OIDC/JWT 검증 미들웨어 도입 및 RBAC(`ADMIN_READ`, `ADMIN_AUDIT`) 적용
- [ ] 감사 로그 스키마/저장 경로 확정(테이블 or 로그 집계)
- [ ] 감사 로그 필드(`who/when/what/result/ip/ua`) 일관화
- [ ] 민감 필드 최소화/마스킹 정책 추가
- [ ] Commit

## Phase 7 — 관측/운영(SLO) 강화
- [ ] API 지표(p50/p95/p99, error rate, QPS) 계측
- [ ] Consumer 지표(lag, DLQ rate, freshness) 계측
- [ ] 트레이싱/코릴레이션 ID 전파
- [ ] (Local) 메트릭 노출(예: /metrics) 및 대시보드 초안
- [ ] SLO 기준 명시: API p95 200ms, 데이터 신선도 p95 5s, 알림 임계치 정의
- [ ] Commit

## Phase 8 — 클라우드 인프라 준비(Azure)
- [ ] (Cloud) Azure PostgreSQL(Flexible) 프로비저닝 및 네트워크 정책 정의
- [ ] (Cloud) Event Hubs(Kafka endpoint) 또는 Managed Kafka 연결 구성
- [ ] (Cloud) ACR + Container Apps/AKS 배포 기본값 확정
- [ ] (Cloud) Key Vault + Managed Identity로 시크릿 전달
- [ ] (Cloud) App Insights/Log Analytics 연동
- [ ] (Cloud) Backoffice DB 접근 제어(네트워크/계정) 정책 확정
- [ ] Commit

## Phase 9 — 배포/운영 파이프라인 + 테스트 체계
- [ ] CI: lint + unit + integration(컨테이너) 기본 게이트 구성
- [ ] CD: 이미지 빌드/스캔 → DB 마이그레이션 → 배포 → 스모크 테스트
- [ ] backfill/재처리(runbook) 및 DLQ replay 절차 문서화
- [ ] 장애/데이터 불일치 대응 체크리스트 정리
- [ ] 토픽 스키마/계약 테스트를 CI에 연결
- [ ] Commit

## Phase 10 — 안정화 및 문서화
- [ ] 성능 튜닝(쿼리 플랜/인덱스/커넥션 풀) 점검 및 개선
- [ ] 페어링 품질/데이터 신선도 SLO 목표치 확정
- [ ] 운영/보안 문서화(접근 제어, 감사 로그 보관, 키 회전)
- [ ] 아키텍처/데이터 흐름/테이블 스키마 문서 최신화
- [ ] Commit

## Phase별 산출물 체크리스트

### Phase 1
- [x] 디렉터리 골격 생성 완료
- [x] 공통 설정/로깅 스켈레톤 확정
- [x] (Local) Docker compose로 DB/브로커 기동 확인
- [x] 환경 분리 규칙 문서화

### Phase 2
- [x] Backoffice DB 스키마/인덱스 확정
- [x] Alembic 마이그레이션 적용 확인
- [x] upsert 헬퍼/DB 레이어 동작 확인
- [x] (Local) 샘플 데이터 seed 확인
- [x] (옵션) `bo.admin_tx_search` 설계 결정

### Phase 3
- [x] backfill 스크립트/경로 검증
- [x] Consumer 기본 동작(consume→upsert) 확인
- [x] 최신판 정책(`updated_at/version`) 적용 확인
- [x] `ingested_at` LWW 정책 적용 확인
- [x] `ingested_at` 기록/지표 산출 확인
- [x] DLQ 스켈레톤 동작 확인
- [x] 토픽/필수 필드 체크리스트 검증

### Phase 4
- [x] 페어링 부분/완성 케이스 동작 확인
- [x] `pair_incomplete` 지표 산출 확인
- [x] out-of-order 테스트 통과

### Phase 5
- [ ] `GET /admin/tx/{tx_id}` 응답 스키마 확정
- [ ] `pairing_status`/`data_lag_sec` 계산 확인
- [ ] 404/기본값(`related_type`, `status_group`) 처리 확인
- [ ] (Local) E2E 스모크 테스트 통과

### Phase 6
- [ ] RBAC 적용 확인
- [ ] 감사 로그 저장/집계 확인
- [ ] 민감 필드 최소화 정책 반영

### Phase 7
- [ ] API/Consumer 핵심 지표 노출 확인
- [ ] 트레이싱/코릴레이션 ID 전파 확인
- [ ] (Local) 대시보드 초안 확인
- [ ] SLO 기준 및 알림 임계치 확정

### Phase 8
- [ ] (Cloud) DB/브로커/컴퓨트 리소스 생성 확인
- [ ] (Cloud) 시크릿/권한/네트워크 정책 확인
- [ ] (Cloud) 관측 스택 연동 확인

### Phase 9
- [ ] CI/CD 파이프라인 동작 확인
- [ ] 배포 후 스모크 테스트 자동화 확인
- [ ] 재처리/복구 절차 문서화 완료
- [ ] 토픽 스키마/계약 테스트 CI 연동

### Phase 10
- [ ] 성능/안정화 조치 기록
- [ ] SLO 목표/알림 정책 확정
- [ ] 운영/보안/아키텍처 문서 최신화
