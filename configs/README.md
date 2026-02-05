# Environment configuration

Rules
- Use `APP_ENV` to select `local`, `dev`, or `prod`.
- `local` defaults are safe for Docker Compose (no secrets committed).
- `dev`/`prod` must set all connection values via environment variables or secret stores.
- Follow 12-factor practices: never commit credentials.

Required variables (current skeleton)
- `APP_ENV`: `local` | `dev` | `prod`
- `LOG_LEVEL`: `INFO` by default
- `DATABASE_URL`: Backoffice DB connection string
- `KAFKA_BROKERS`: Kafka bootstrap servers
- `SERVICE_NAME`: service identifier for logs/metrics
- `KAFKA_GROUP_ID`: consumer group id
- `LEDGER_TOPIC`: ledger entry topic
- `PAYMENT_ORDER_TOPIC`: payment order topic
- `DLQ_PATH`: local DLQ file path
- `CONSUMER_POLL_TIMEOUT_MS`: Kafka poll timeout in milliseconds
- `CONSUMER_OFFSET_RESET`: Kafka offset reset policy (`earliest`/`latest`)
- `AUTH_MODE`: `disabled` or `oidc`
- `AUTH_ISSUER`: OIDC issuer URL
- `AUTH_AUDIENCE`: expected audience
- `AUTH_JWKS_URL`: JWKS endpoint
- `AUTH_ALGORITHM`: JWT algorithm (default `RS256`)
- `AUTH_ROLES_CLAIM`: roles claim name (default `roles`, comma-separated allowed)
- `AUTH_ACTOR_ID_CLAIMS`: actor id claim priority list (default `sub`)
- `AUDIT_MASK_QUERY_KEYS`: query keys to mask in audit logs
- `DB_POOL_SIZE`: SQLAlchemy pool size (default `5`)
- `DB_MAX_OVERFLOW`: extra overflow connections (default `10`)
- `DB_POOL_TIMEOUT`: seconds to wait for a connection (default `30`)
- `DB_POOL_RECYCLE`: seconds before recycling a connection (default `1800`)

Examples
- Copy `configs/env.example` and export values in your shell.
