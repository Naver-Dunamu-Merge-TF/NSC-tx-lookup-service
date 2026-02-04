Backoffice Serving Layer - LLM Coding Agent Instructions
========================================================

Instructions for LLM coding agents working with the tx-lookup-service codebase.


Project overview
----------------

Backoffice Serving Layer provides **admin transaction lookup (FR-ADM-02)** with
near real-time `tx_id` based queries.

**Components:**
 - **Admin API**: REST API for admin queries (FastAPI)
 - **Sync Consumer**: OLTP → Backoffice DB synchronization
 - **Backoffice DB**: Read-optimized serving store (PostgreSQL)

**Core principles:**
 - Backoffice DB is a **read-only derived store**
 - Write transactions only in OLTP; Backoffice receives via Sync Consumer
 - All upserts must be **idempotent**

See `.specs/backoffice_project_specs.md` for full project specs and decision locks.


Development environment
-----------------------

 - **API**: Python + FastAPI
 - **Consumer**: Python (custom service)
 - **DB**: PostgreSQL (local Docker / Azure)
 - **Events**: Kafka (or Azure Event Hubs)
 - **Testing**: pytest + Docker Compose


Repository structure
--------------------

```
├── src/
│   ├── api/           # Admin API (FastAPI)
│   ├── consumer/      # Sync Consumer
│   ├── db/            # Models & repositories
│   └── common/        # Shared utilities
├── tests/
│   ├── unit/
│   └── integration/
├── migrations/        # Alembic migrations
├── docker/
├── configs/
└── .specs/            # Specifications (SSOT)
```


Key domain concepts
-------------------

 - `tx_id`: Ledger entry ID (PK)
 - `related_id`: Pairing key (= `payment_orders.order_id`)
 - Double-entry: PAYMENT + RECEIVE have different `tx_id`, same `related_id`

See `.specs/backoffice_db_admin_api.md` for DB schema and API design.


Code patterns
-------------

 - **Idempotency**: Upsert by key (`tx_id`, `order_id`), latest-wins by `updated_at`
 - **Pairing**: Allow partial pairs; track `pair_incomplete` status
 - **API responses**: 404 if not found; 200 with `pairing_status` if incomplete

See `.specs/backoffice_data_project.md` for sync and pairing details.


Verification policy
-------------------

### Verification contract

 - Verification is mandatory. Do not claim completion without running an
   appropriate verification level.
 - Store evidence under `.agents/logs/verification/`.
 - Do not encode verification level in commit messages.

### Verification ladder

| Level | When | Command |
|-------|------|---------|
| L0 | Per edit | `python -m py_compile` |
| L1 | Pre-commit | `pytest tests/unit/ -x` |
| L2 | Pre-PR | `pytest --cov-fail-under=80` |
| L3 | Pre-merge | Docker Compose E2E |

**Escalation:** L3 required for pairing logic or response schema changes.


Security & observability
------------------------

 - Auth: OIDC/JWT, RBAC (`ADMIN_READ`, `ADMIN_AUDIT`)
 - Audit logs required for all queries
 - SLO: API p95 < 200ms, data freshness p95 < 5s

See `.specs/backoffice_project_specs.md` sections 7-8.


Key references
--------------

**Consult `.specs/` as SSOT for all design decisions.**

| Document | Content |
|----------|---------|
| `.specs/SRS - Software Requirements Specification.md` | Requirements (FR-ADM-02) |
| `.specs/backoffice_project_specs.md` | Project specs, Decision Lock |
| `.specs/backoffice_db_admin_api.md` | DB + API design |
| `.specs/backoffice_data_project.md` | Sync specs |
| `.specs/database_schema` | OLTP schema |
